import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from time import monotonic

from redis.lock import Lock
from sqlalchemy.orm import Session

from codegraph.configs.indexing import (
    DIRECTORY_SKIP_INDEXING_PATTERN,
    FILETYPE_LANGUAGES,
    INDEXED_FILETYPES,
    MAX_INDEXING_FILE_SIZE,
    MAX_INDEXING_WORKERS,
)
from codegraph.db.engine import get_session
from codegraph.db.models import File, Project
from codegraph.graph.indexing.parsing.python_parser import PythonParser
from codegraph.graph.models import IndexingStatus, IndexingStep, Language
from codegraph.redis.lock_utils import extend_lock
from codegraph.utils.logging import get_logger

logger = get_logger()

# NOTE: make sure to update `PARSER_CLASSES` when creating a new parser
PARSER_CLASSES = [PythonParser]

_PARSER_CLASSES_BY_LANGUAGE = {
    parser_cls._LANGUAGE: parser_cls
    for parser_cls in PARSER_CLASSES
    if parser_cls._LANGUAGE is not None
}


def create_project(project_name: str, project_root: Path) -> int:
    """
    Creates a `Project` along with its root `File` and adds it to the database. Returns the project
    id.
    """
    assert project_root.is_dir()
    project_root = project_root.resolve()

    with get_session() as session:
        db_project = Project(name=project_name, root_path=project_root.as_posix())
        session.add(db_project)
        session.flush()

        project_id = db_project.id
        root_file = _create_file(project_root, project_id, None, None, session)
        db_project.root_file_id = root_file.id
        session.commit()

    return project_id


def run_indexing(
    project_id: int,
    lock: Lock | None = None,
    directory_skip_pattern: str = DIRECTORY_SKIP_INDEXING_PATTERN,
    max_filesize: float = MAX_INDEXING_FILE_SIZE,
) -> IndexingStatus:
    """
    Runs the complete (re)indexing pipeline for a given project. Indexing for the same project
    should not overlap. If a lock is provided, it will ensure it does not expire while indexing.
    TODO: make indexing crash safe
    """
    indexing_start_time = datetime.now()
    last_locked_at = monotonic()

    with get_session() as session:
        # 1. Find project root
        db_project = session.query(Project).filter(Project.id == project_id).one()
        project_root = Path(db_project.root_path)
        root_file = db_project.root_file
        assert root_file is not None
        assert root_file.path == project_root.as_posix()

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

        # 3. Create cg indexing wrapper
        def _cg_indexing_wrapper(filepath: Path, language: Language, step: IndexingStep) -> None:
            with get_session() as cg_session:
                parser_cls = _PARSER_CLASSES_BY_LANGUAGE[language]
                parser = parser_cls(project_id, project_root, filepath, cg_session)

                if step == IndexingStep.DEFINITIONS:
                    parser.extract_definitions()
                elif step == IndexingStep.REFERENCES:
                    parser.extract_references()
                cg_session.commit()

        # 4. Traverse from root to find new/modified `File`s and track indexing tasks + languages
        cg_tasks: list[tuple[Path, Language]] = []
        vec_tasks: list[Path] = []
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
            run_indexing = False

            # delete `File` if it's a file and has been modified since last indexed
            updated_at = datetime.fromtimestamp(file_stats.st_mtime)
            if (
                current_file is not None
                and path.is_file()
                and updated_at > current_file.last_indexed_at
            ):
                session.delete(current_file)
                session.flush()
                current_file = None

            # create file if not previously indexed
            if current_file is None:
                if path.is_dir():
                    current_file = _create_file(path, project_id, parent_file, None, session)
                    stack.extend((path, current_file) for path in path.iterdir())
                    continue

                current_file = _create_file(path, project_id, parent_file, language, session)
                run_indexing = True

            # update `File` last indexed time
            current_file.last_indexed_at = datetime.now()

            # add codegraph and vector indexing tasks
            if not run_indexing:
                continue
            if language in _PARSER_CLASSES_BY_LANGUAGE:
                cg_tasks.append((path, language))
            vec_tasks.append(path)

        # delete files that haven't been touched
        session.query(File).filter(
            File.project_id == project_id, File.last_indexed_at < indexing_start_time
        ).delete(synchronize_session=False)

        # update project languages
        db_project.languages = list(project_languages)

        session.commit()

    # 5. Run indexing tasks
    logger.info(
        f"Starting codegraph indexing of {len(cg_tasks)} files and "
        f"vector indexing of {len(vec_tasks)} files for project {project_id}."
    )
    with ThreadPoolExecutor(max_workers=MAX_INDEXING_WORKERS) as executor:
        # 5.1. Run codegraph definition extraction
        cg1_futs = [
            executor.submit(_cg_indexing_wrapper, path, language, IndexingStep.DEFINITIONS)
            for path, language in cg_tasks
        ]
        for fut in as_completed(cg1_futs):
            fut.result()  # re-raise any exceptions immediately
            if lock:
                last_locked_at = extend_lock(lock, last_locked_at)

        # 5.2. Run codegraph reference extraction and vector indexing
        cg2_futs = [
            executor.submit(_cg_indexing_wrapper, path, language, IndexingStep.REFERENCES)
            for path, language in cg_tasks
        ]
        # vec_futs = [executor.submit(VECTOR_INDEX_FN, path) for path in vec_tasks]
        for fut in as_completed(cg2_futs):  # + vec_futs
            fut.result()  # re-raise any exceptions immediately
            if lock:
                last_locked_at = extend_lock(lock, last_locked_at)

    return IndexingStatus(
        start_time=indexing_start_time,
        duration=datetime.now() - indexing_start_time,
        codegraph_indexed_paths=[path for path, _ in cg_tasks],
        vector_indexed_paths=vec_tasks,
    )


def _find_file(filepath: Path, project_id: int, session: Session) -> File | None:
    """
    Finds a `File` object in the database.
    """
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
    session: Session,
) -> File:
    """
    Creates a `File` object and adds it to the database. Does not commit the session.
    """
    file_stats = filepath.stat()
    created_at = datetime.fromtimestamp(file_stats.st_ctime)
    updated_at = datetime.fromtimestamp(file_stats.st_mtime)

    db_file = File(
        name=filepath.name,
        path=filepath.as_posix(),
        language=language,
        created_at=created_at,
        updated_at=updated_at,
        parent_id=parent.id if parent is not None else None,
        project_id=project_id,
    )
    session.add(db_file)

    session.flush()
    return db_file
