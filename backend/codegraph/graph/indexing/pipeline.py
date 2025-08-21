import re
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from codegraph.configs.indexing import (
    CODEGRAPH_SUPPORTED_FILETYPES,
    DIRECTORY_SKIP_INDEXING_PATTERN,
    INDEXED_FILETYPES,
    MAX_INDEXING_FILE_SIZE,
    MAX_INDEXING_WORKERS,
)
from codegraph.db.engine import get_session
from codegraph.db.models import File, Project
from codegraph.graph.indexing.parsing.base_parser import BaseParser
from codegraph.graph.indexing.parsing.python_parser import PythonParser
from codegraph.graph.models import Language
from codegraph.utils.logging import get_logger

logger = get_logger()

# NOTE: make sure to update this when creating a new parser
PARSER_CLASSES = [PythonParser]


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

    # 2. Initialize parsers
    parsers: dict[Language, BaseParser] = {
        parser_cls._LANGUAGE: parser_cls(project_id, project_root)
        for parser_cls in PARSER_CLASSES
        if parser_cls._LANGUAGE is not None
    }

    # 3. Traverse from root to create `File`s and track files to index
    cg1_tasks: list[tuple[Callable[[Path], None], Path]] = []
    cg2_tasks: list[tuple[Callable[[Path], None], Path]] = []
    vec_paths: list[Path] = []
    path_stack: list[Path] = [project_root]

    with get_session() as session:
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
            language = CODEGRAPH_SUPPORTED_FILETYPES.get(path.suffix)
            if language is not None:
                cg1_tasks.append((parsers[language].extract_definitions, path))
                cg2_tasks.append((parsers[language].extract_references, path))
                _create_file(path, project_id, language, session)

            # add vector indexing task
            if path.suffix in INDEXED_FILETYPES:
                vec_paths.append(path)
        session.commit()

    # 4. Run indexing tasks
    logger.info(
        f"Starting codegraph indexing of {len(cg1_tasks)} files and "
        f"vector indexing of {len(vec_paths)} files."
    )
    with ThreadPoolExecutor(max_workers=MAX_INDEXING_WORKERS) as executor:
        cg1_futs = [executor.submit(task, path) for task, path in cg1_tasks]
        # vec_futs = [executor.submit(VECTOR_INDEX_FN, path) for path in vec_paths]

        # wait for cg1 to finish, then queue cg2
        wait(cg1_futs)
        # cg2_futs = [executor.submit(task, path) for task, path in cg2_tasks]

        # wait(cg2_futs + vec_futs)


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
