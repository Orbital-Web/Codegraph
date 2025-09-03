import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Generator
from uuid import UUID

from redis.lock import Lock
from sqlalchemy import select
from sqlalchemy.orm import Session

from codegraph.configs.indexing import (
    DIRECTORY_SKIP_INDEXING_PATTERN,
    FILETYPE_LANGUAGES,
    INDEXED_FILETYPES,
    INDEXING_BATCH_SIZE,
    INDEXING_CHUNK_OVERLAP,
    INDEXING_CHUNK_SIZE,
    MAX_INDEXING_FILE_SIZE,
    MAX_INDEXING_WORKERS,
)
from codegraph.db.engine import get_session
from codegraph.db.models import File, Project
from codegraph.graph.indexing.chunking.chunker import Chunker
from codegraph.graph.indexing.parsing.base_parser import BaseParser
from codegraph.graph.indexing.parsing.python_parser import PythonParser
from codegraph.graph.models import (
    INDEXING_STEP_ORDER,
    NEXT_INDEXING_STEPS,
    IndexingStatus,
    IndexingStep,
    Language,
)
from codegraph.index.chroma import ChromaIndexManager
from codegraph.redis.lock_utils import extend_lock
from codegraph.utils.logging import get_logger

logger = get_logger()

# NOTE: make sure to update `PARSER_CLASSES` when creating a new parser
PARSER_CLASSES = [PythonParser]

_PARSER_CLASSES_BY_LANGUAGE: dict[Language, type[BaseParser]] = {
    parser_cls._LANGUAGE: parser_cls for parser_cls in PARSER_CLASSES
}


def create_project(project_name: str, project_root: Path) -> int:
    """Creates a `Project` along with its root `File` and adds it to the database. Returns the
    project id.
    """
    assert project_root.is_dir()
    project_root = project_root.resolve()

    with get_session() as session:
        db_project = Project(name=project_name, root_path=project_root.as_posix())
        session.add(db_project)
        session.flush()

        project_id = db_project.id
        root_file = _create_file(
            project_root, project_id, None, None, IndexingStep.COMPLETE, session
        )  # root so no parent, dir so no language and no indexing step
        db_project.root_file_id = root_file.id
        session.commit()

    return project_id


def run_indexing(
    project_id: int,
    lock: Lock | None = None,
    *,
    directory_skip_pattern: str = DIRECTORY_SKIP_INDEXING_PATTERN,
    max_filesize: float = MAX_INDEXING_FILE_SIZE,
    chunk_size: int = INDEXING_CHUNK_SIZE,
    chunk_overlap: int = INDEXING_CHUNK_OVERLAP,
    batch_size: int = INDEXING_BATCH_SIZE,
) -> IndexingStatus:
    """Runs the complete (re)indexing pipeline for a given project. Indexing for the same project
    should not overlap. If a lock is provided, it will ensure it does not expire while indexing.
    The indexing will pick up where it left off in case of a crash.
    """
    indexing_start_time = datetime.now()
    last_locked_at = monotonic()

    with get_session() as session:
        # 1. Find project root
        db_project = session.query(Project).filter(Project.id == project_id).one()
        project_root = Path(db_project.root_path)
        root_file = db_project.root_file
        assert root_file is not None
        assert root_file.path == db_project.root_path

        # 2. Delete project if root no longer exists, otherwise update last indexed time
        if not project_root.exists():
            session.delete(db_project)
            session.commit()
            return IndexingStatus(
                start_time=indexing_start_time,
                duration=datetime.now() - indexing_start_time,
                codegraph_indexed_paths=[],
                vector_indexed_paths=[],
            )
        root_file.last_indexed_at = datetime.now()

        # 3. Create indexing helpers
        chunker = Chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        index = ChromaIndexManager.get_or_create_index(project_id)

        def _indexing_wrapper(_file_id: UUID) -> None:
            with get_session() as _session:
                _file = _session.query(File).filter(File.id == _file_id).one()
                assert _file.indexing_step != IndexingStep.COMPLETE

                _step = _file.indexing_step
                _filepath = Path(_file.path)

                # codegraph indexing
                if _step in (IndexingStep.DEFINITIONS, IndexingStep.REFERENCES):
                    assert _file.language is not None
                    _parser_cls = _PARSER_CLASSES_BY_LANGUAGE[_file.language]
                    _parser = _parser_cls(project_id, project_root, _filepath, _session)

                    if _step == IndexingStep.DEFINITIONS:
                        _parser.extract_definitions()
                    else:
                        _parser.extract_references()

                # vector indexing
                elif _step == IndexingStep.VECTOR:
                    if _chunks := chunker.chunk(_file, _session):
                        index.upsert(_chunks)
                        _file.chunks = len(_chunks)

                # update step
                _file.indexing_step = NEXT_INDEXING_STEPS[_step]
                _session.commit()

        # 4. Index `File`s, set appropriate indexing step, and track languages
        project_languages: set[Language] = set()

        skip_pattern = re.compile(directory_skip_pattern)
        stack: list[tuple[Path, File]] = [(path, root_file) for path in project_root.iterdir()]
        while stack:
            path, parent_file = stack.pop()

            if lock:
                last_locked_at = extend_lock(lock, last_locked_at)

            # check for skip conditions
            file_stats = path.stat()
            if (
                (path.is_dir() and skip_pattern.match(path.name))
                or (path.is_file() and file_stats.st_size > max_filesize * 1024 * 1024)
                or (path.is_file() and path.suffix not in INDEXED_FILETYPES)
            ):
                continue

            language = FILETYPE_LANGUAGES.get(path.suffix)
            if language is not None:
                project_languages.add(language)

            current_file = _find_file(path, project_id, session)

            # delete `File` and its chunks if it's a file and has been modified since last indexed
            updated_at = datetime.fromtimestamp(file_stats.st_mtime)
            if (
                current_file is not None
                and path.is_file()
                and updated_at > current_file.last_indexed_at
            ):
                index.delete(current_file)
                session.delete(current_file)
                session.flush()
                current_file = None

            # create file if not previously indexed, otherwise update last indexed time
            if current_file is None:
                if path.is_dir():
                    current_file = _create_file(
                        path, project_id, parent_file, None, IndexingStep.COMPLETE, session
                    )  # dir so no language and no indexing step
                else:
                    current_file = _create_file(
                        path,
                        project_id,
                        parent_file,
                        language,
                        (
                            IndexingStep.DEFINITIONS
                            if language in _PARSER_CLASSES_BY_LANGUAGE
                            else IndexingStep.VECTOR
                        ),  # do codegraph indexing if language is supported, otherwise vector only
                        session,
                    )
            else:
                current_file.last_indexed_at = datetime.now()

            # add subdirectories to stack and continue
            if path.is_dir():
                stack.extend((path, current_file) for path in path.iterdir())

        # find files that haven't been touched
        deleted_file_ids = list(
            session.execute(
                select(File.id).filter(
                    File.project_id == project_id, File.last_indexed_at < indexing_start_time
                )
            )
            .scalars()
            .all()
        )

        # delete files that haven't been touched, and their chunks
        if deleted_file_ids:
            index.delete_ids(deleted_file_ids, session)
            session.query(File).filter(File.id.in_(deleted_file_ids)).delete(
                synchronize_session=False
            )

        # update project languages
        db_project.languages = list(project_languages)

        session.commit()

    # 5. Run indexing tasks
    logger.info(f"Starting codegraph indexing for project {project_id}.")
    cg_paths: list[Path] = []
    vec_paths: list[Path] = []

    with ThreadPoolExecutor(max_workers=MAX_INDEXING_WORKERS) as executor:
        for step in INDEXING_STEP_ORDER:
            for files in _get_batch_files_at_step(project_id, step, batch_size=batch_size):
                # batch index
                futs = [executor.submit(_indexing_wrapper, file.id) for file in files]
                for fut in as_completed(futs):
                    fut.result()

                # extend locks and track indexed paths
                if lock:
                    last_locked_at = extend_lock(lock, last_locked_at)
                if step == IndexingStep.REFERENCES:
                    cg_paths.extend(Path(file.path) for file in files)
                elif step == IndexingStep.VECTOR:
                    vec_paths.extend(Path(file.path) for file in files)

    return IndexingStatus(
        start_time=indexing_start_time,
        duration=datetime.now() - indexing_start_time,
        codegraph_indexed_paths=cg_paths,
        vector_indexed_paths=vec_paths,
    )


def _find_file(filepath: Path, project_id: int, session: Session) -> File | None:
    """Finds a `File` object in the database."""
    return (
        session.query(File)
        .filter(File.project_id == project_id, File.path == filepath.as_posix())
        .one_or_none()
    )


def _create_file(
    filepath: Path,
    project_id: int,
    parent: File | None,
    language: Language | None,
    indexing_step: IndexingStep,
    session: Session,
) -> File:
    """Creates a `File` object and adds it to the database. Does not commit the session."""
    file_stats = filepath.stat()
    created_at = datetime.fromtimestamp(file_stats.st_ctime)
    updated_at = datetime.fromtimestamp(file_stats.st_mtime)

    db_file = File(
        name=filepath.name,
        path=filepath.as_posix(),
        language=language,
        indexing_step=indexing_step,
        created_at=created_at,
        updated_at=updated_at,
        parent_id=parent.id if parent is not None else None,
        project_id=project_id,
    )
    session.add(db_file)

    session.flush()
    return db_file


def _get_batch_files_at_step(
    project_id: int, indexing_step: IndexingStep, batch_size: int = INDEXING_BATCH_SIZE
) -> Generator[list[File], None, None]:
    """Generator that yields `File`s to index at a given `indexing_step`."""
    assert indexing_step != IndexingStep.COMPLETE

    while True:
        with get_session() as session:
            files = (
                session.query(File)
                .filter(File.project_id == project_id, File.indexing_step == indexing_step)
                .limit(batch_size)
                .all()
            )
        if not files:
            break
        yield files
