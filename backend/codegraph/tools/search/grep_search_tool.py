# TODO: write test cases
import asyncio
import shutil
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from codegraph.db.engine import get_session
from codegraph.db.models import Project
from codegraph.tools.shared_models import ToolHiddenArgError
from codegraph.utils.logging import get_logger

logger = get_logger()

app = FastMCP(__name__)


@app.tool(exclude_args=["project_id"])
async def grep_file(
    pattern: Annotated[
        str,
        (
            "The pattern to search for. Treated as a string literal if `use_regex=False`. "
            "Otherwise, treated as a (extended) regular expression. E.g., '[0-9]+' will match "
            "the literal string if `use_regex=False`, otherwise it will match for digits."
        ),
    ],
    path: Annotated[
        str | list[str],
        (
            "Filepath(s) to search for. These should be files, not directories, and should be "
            "relative to the project root directory or absolute."
        ),
    ],
    use_regex: Annotated[
        bool, "Whether to use string literals for `pattern` or regular expressions."
    ] = False,
    ignore_case: Annotated[bool, "Whether to ignore cases when finding matches"] = False,
    max_matches: Annotated[
        int | None, "Maximum number of matches to find, or unlimited if `None`"
    ] = None,
    context_before: Annotated[int, "Number of lines before the match to include"] = 0,
    context_after: Annotated[int, "Number of lines after the match to include"] = 0,
    # runtime arguments
    project_id: int = -1,
) -> list[str]:
    """Search for a `pattern` in one or more files."""
    if project_id == -1:
        raise ToolHiddenArgError("`project_path` not set correctly.")

    # get project root
    with get_session() as session:
        project_root = Path(
            session.query(Project.root_path).filter(Project.id == project_id).scalar()
        )

    # build args
    args = [
        arg
        for arg in (
            "-n",  # include line numbers
            "-I",  # skip binaries
            "-E" if use_regex else "-F",
            "-i" if ignore_case else None,
            f"-m {max_matches}" if max_matches else None,
            f"-B {context_before}" if context_before else None,
            f"-A {context_after}" if context_after else None,
        )
        if arg is not None
    ]
    args.append(pattern)
    args.extend([path] if isinstance(path, str) else path)

    proc = await asyncio.create_subprocess_exec(
        "grep",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=project_root,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode == 2:
        raise ToolError(f"grep failed with code {proc.returncode}: {stderr.decode()}")
    elif proc.returncode == 1:
        return []

    # TODO: send response as a pydantic model in shared_models.py
    return stdout.decode().split("\n")


@app.tool(exclude_args=["project_id"])
async def grep_dir(
    pattern: Annotated[
        str,
        (
            "The pattern to search for. Treated as a string literal if `use_regex=False`. "
            "Otherwise, treated as a (extended) regular expression. E.g., '[0-9]+' will match "
            "the literal string if `use_regex=False`, otherwise it will match for digits."
        ),
    ],
    path: Annotated[
        str | list[str],
        (
            "Dirpath(s) to search for. These should be directories, not files, and should be "
            "relative to the project root directory or absolute."
        ),
    ],
    use_regex: Annotated[
        bool, "Whether to use string literals for `pattern` or regular expressions."
    ] = False,
    ignore_case: Annotated[bool, "Whether to ignore cases when finding matches"] = False,
    max_matches: Annotated[
        int | None, "Maximum number of matches to find, or unlimited if `None`"
    ] = None,
    context_before: Annotated[int, "Number of lines before the match to include"] = 0,
    context_after: Annotated[int, "Number of lines after the match to include"] = 0,
    exclude_dir: Annotated[
        str | list[str] | None,
        (
            "Glob pattern for directories to skip. E.g., if `exclude_dir=['.?*', 'abc']`, "
            "it will skip hidden directories and the `abc` directory. Defaults to `No"
        ),
    ] = None,
    include: Annotated[
        str | list[str] | None,
        (
            "Glob pattern for files to include. If this parameter is provided, only files matching "
            "these globs will be included. E.g., if `include='*.py'`, it will only include "
            "matches from python files."
        ),
    ] = None,
    exclude: Annotated[
        str | list[str] | None,
        (
            "Glob pattern for files to exclude. E.g., if `exclude=['secret*','*.cpp']`, "
            "matches in cpp files or files starting with 'secret' will be excluded."
        ),
    ] = None,
    # runtime arguments
    project_id: int = -1,
) -> list[str]:
    """Search recursively for a `pattern` in one or more directories"""
    if project_id == -1:
        raise ToolHiddenArgError("`project_path` not set correctly.")

    # get project root
    with get_session() as session:
        project_root = Path(
            session.query(Project.root_path).filter(Project.id == project_id).scalar()
        )

    # build args
    args = [
        arg
        for arg in (
            "-n",  # include line numbers
            "-I",  # skip binaries
            "-r",  # recursive
            "-E" if use_regex else "-F",
            "-i" if ignore_case else None,
            f"-m {max_matches}" if max_matches else None,
            f"-B {context_before}" if context_before else None,
            f"-A {context_after}" if context_after else None,
        )
        if arg is not None
    ]
    if exclude_dir is not None:
        for i in exclude_dir if isinstance(exclude_dir, list) else [exclude_dir]:
            args.append(f"--exclude-dir='{i}'")
    if include is not None:
        for i in include if isinstance(include, list) else [include]:
            args.append(f"--include='{i}'")
    if exclude is not None:
        for i in exclude if isinstance(exclude, list) else [exclude]:
            args.append(f"--exclude='{i}'")
    args.append(pattern)
    args.extend([path] if isinstance(path, str) else path)

    proc = await asyncio.create_subprocess_exec(
        "grep",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=project_root,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode == 2:
        raise ToolError(f"grep failed with code {proc.returncode}: {stderr.decode()}")
    elif proc.returncode == 1:
        return []

    # TODO: send response as a pydantic model in shared_models.py
    return stdout.decode().split("\n")


if not shutil.which("grep"):
    logger.warning("grep isn't available on this system, grep tools will be disabled")
    grep_file.disable()
    grep_dir.disable()
