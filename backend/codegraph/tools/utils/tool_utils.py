from pathlib import Path

from codegraph.db.engine import get_session
from codegraph.db.models import Project
from codegraph.tools.shared_models import InternalToolCallError


def get_project_root(project_id: int) -> Path:
    if project_id == -1:
        raise InternalToolCallError("`project_id` not set correctly.")

    with get_session() as session:
        project_root_str: str | None = (
            session.query(Project.root_path).filter(Project.id == project_id).scalar()
        )
    if project_root_str is None:
        raise InternalToolCallError("Project with given `project_id` doesn't exist.")
    return Path(project_root_str)


def resolve_paths(paths: list[str], base_path: Path) -> list[str]:
    """Takes in a list of relative or absolute paths and converts them all into resolved absolute
    paths. Raises an error if the paths aren't under `base_path`.
    """
    resolved: list[str] = []
    for p in paths:
        path = Path(p)
        if path.is_absolute():
            rpath = path.resolve(strict=True)
            resolved.append(path.resolve(strict=True).as_posix())

            # raise error if path is not under base path
            if not rpath.is_relative_to(base_path):
                raise ValueError(f"Path {path.as_posix()} is not a valid path within the project")
        else:
            rpath = (base_path / path).resolve(strict=True)
        resolved.append(rpath.as_posix())

    return resolved
