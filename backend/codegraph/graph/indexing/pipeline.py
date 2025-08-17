import re
from concurrent.futures import ThreadPoolExecutor
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
from codegraph.graph.models import Language


def run_indexing(project_id: int, project_root: Path) -> None:
    """
    Runs the indexing pipeline for a given project. Assumes the `Project` already exists.
    TODO: handle incremental indexing/reindexing after failure
    """
    # 0. Initialize
    parsers: dict[Language, BaseParser] = {
        parser_cls._LANGUAGE: parser_cls(project_id, project_root)  # type: ignore[abstract]
        for parser_cls in BaseParser.__subclasses__()
        if parser_cls._LANGUAGE is not None
    }
    skip_pattern = re.compile(DIRECTORY_SKIP_INDEXING_PATTERN)

    # 1. Traverse from root to create `File`s and track which files to index
    indexing_tasks: list[tuple[Callable[[Path], None], Path]] = []
    path_stack: list[Path] = [project_root]

    with get_session() as session:
        while path_stack:
            path = path_stack.pop()

            # handle directories
            if path.is_dir():
                if skip_pattern.match(path.name):
                    continue
                _create_file(path, project_id, project_root, None, session)
                path_stack.extend(path.iterdir())
                continue

            # handle files
            filesize = path.stat().st_size
            if filesize > MAX_INDEXING_FILE_SIZE * 1024 * 1024:
                continue

            # add codegraph indexing task
            language = CODEGRAPH_SUPPORTED_FILETYPES.get(path.suffix)
            if language is not None:
                indexing_tasks.append((parsers[language].extract_definitions, path))
                _create_file(path, project_id, project_root, language, session)

            # add vector database indexing task
            if path.suffix in INDEXED_FILETYPES:
                # TODO: indexing_tasks.append((INDEXING_FN, path))
                pass
        session.commit()

    # 2. Run indexing tasks in parallel
    with ThreadPoolExecutor(max_workers=MAX_INDEXING_WORKERS) as executor:
        for task, path in indexing_tasks:
            executor.submit(task, path)


def _create_file(
    filepath: Path, project_id: int, project_root: Path, language: Language | None, session: Session
) -> File:
    """
    Creates a `File` object and adds it to the database. Commits the session. If `filepath` is the
    project root, it is added to the `Project` object.
    """
    file_stats = filepath.stat()
    created_at = datetime.fromtimestamp(file_stats.st_ctime)
    updated_at = datetime.fromtimestamp(file_stats.st_mtime)

    parent_path = filepath.parent
    parent = (
        session.query(File)
        .filter(File.path == parent_path, File.project_id == project_id)
        .one_or_none()
    )
    parent_id = parent.id if parent else None

    db_file = File(
        name=filepath.name,
        path=filepath,
        language=language,
        created_at=created_at,
        updated_at=updated_at,
        parent_id=parent_id,
        project_id=project_id,
    )
    session.add(db_file)

    if filepath == project_root:
        project = session.get(Project, project_id)
        assert project is not None
        assert project.root_file_id is None
        project.root_file_id = db_file.id

    session.commit()
    return db_file
