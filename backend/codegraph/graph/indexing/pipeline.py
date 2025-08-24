import re
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from codegraph.configs.indexing import (
    DIRECTORY_SKIP_INDEXING_PATTERN,
    FILETYPE_LANGUAGES,
    MAX_INDEXING_FILE_SIZE,
    MAX_INDEXING_WORKERS,
    VECTOR_INDEXED_FILETYPES,
)
from codegraph.db.engine import get_session
from codegraph.db.models import File, Project
from codegraph.graph.indexing.parsing.python_parser import PythonParser
from codegraph.graph.models import IndexingStep, Language
from codegraph.utils.logging import get_logger

logger = get_logger()

# NOTE: make sure to update `PARSER_CLASSES` when creating a new parser
PARSER_CLASSES = [PythonParser]

_PARSER_CLASSES_BY_LANGUAGE = {
    parser_cls._LANGUAGE: parser_cls
    for parser_cls in PARSER_CLASSES
    if parser_cls._LANGUAGE is not None
}


def run_indexing(project_name: str, project_root: Path) -> None:
    """
    Runs the complete indexing pipeline for a given project.
    TODO: handle incremental indexing/reindexing after failure
    """
    assert project_root.is_dir()
    project_root = project_root.resolve()
    skip_pattern = re.compile(DIRECTORY_SKIP_INDEXING_PATTERN)

    # 1. Create `Project` and root `File`
    with get_session() as session:
        db_project = Project(name=project_name)
        session.add(db_project)
        session.flush()

        project_id = db_project.id
        root_file = _create_file(project_root, project_id, None, session)
        db_project.root_file_id = root_file.id
        session.commit()

    # 2. Create cg indexing wrapper
    def _cg_indexing_wrapper(filepath: Path, language: Language, step: IndexingStep) -> None:
        with get_session() as session:
            parser_cls = _PARSER_CLASSES_BY_LANGUAGE[language]
            parser = parser_cls(project_id, project_root, filepath, session)

            if step == IndexingStep.DEFINITIONS:
                parser.extract_definitions()
            elif step == IndexingStep.REFERENCES:
                parser.extract_references()
            session.commit()

    # 3. Traverse from root to create `File`s and track languages + files to index
    cg_tasks: list[tuple[Path, Language]] = []
    vec_tasks: list[Path] = []
    project_languages: set[Language] = set()

    with get_session() as session:
        path_stack: list[Path] = [project_root]
        while path_stack:
            path = path_stack.pop()

            # handle directories
            if path.is_dir():
                if skip_pattern.match(path.name):
                    continue
                if path != project_root:
                    _create_file(path, project_id, None, session)
                path_stack.extend(path.iterdir())
                continue

            # handle files
            filesize = path.stat().st_size
            if filesize > MAX_INDEXING_FILE_SIZE * 1024 * 1024:
                continue

            # add codegraph indexing tasks
            language = FILETYPE_LANGUAGES.get(path.suffix)
            if language is not None:
                project_languages.add(language)
                if language in _PARSER_CLASSES_BY_LANGUAGE:
                    cg_tasks.append((path, language))
                    _create_file(path, project_id, language, session)

            # add vector indexing task
            if path.suffix in VECTOR_INDEXED_FILETYPES:
                vec_tasks.append(path)

        db_project = session.query(Project).filter(Project.id == project_id).one()
        db_project.languages = list(project_languages)
        session.commit()

    # 4. Run indexing tasks
    logger.info(
        f"Starting codegraph indexing of {len(cg_tasks)} files and "
        f"vector indexing of {len(vec_tasks)} files."
    )
    with ThreadPoolExecutor(max_workers=MAX_INDEXING_WORKERS) as executor:
        cg1_futs = [
            executor.submit(_cg_indexing_wrapper, path, language, IndexingStep.DEFINITIONS)
            for path, language in cg_tasks
        ]
        # vec_futs = [executor.submit(VECTOR_INDEX_FN, path) for path in vec_tasks]

        # wait for cg1 to finish, then queue cg2
        wait(cg1_futs)
        cg2_futs = [
            executor.submit(_cg_indexing_wrapper, path, language, IndexingStep.REFERENCES)
            for path, language in cg_tasks
        ]
        wait(cg2_futs)  # + vec_futs


def _create_file(
    filepath: Path, project_id: int, language: Language | None, session: Session
) -> File:
    """
    Creates a `File` object and adds it to the database. Does not commit the session.
    """
    file_stats = filepath.stat()
    created_at = datetime.fromtimestamp(file_stats.st_ctime)
    updated_at = datetime.fromtimestamp(file_stats.st_mtime)

    parent_path = filepath.parent
    parent = (
        session.query(File)
        .filter(File.path == parent_path.as_posix(), File.project_id == project_id)
        .one_or_none()
    )
    parent_id = parent.id if parent else None

    db_file = File(
        name=filepath.name,
        path=filepath.as_posix(),
        language=language,
        created_at=created_at,
        updated_at=updated_at,
        parent_id=parent_id,
        project_id=project_id,
    )
    session.add(db_file)

    session.flush()
    return db_file
