# TODO: write test cases with malicious input, e.g., pattern = " && rm -rf
import asyncio
import re
import shutil
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from codegraph.configs.tools import GREP_MAX_CONTEXT, GREP_MAX_MATCHES
from codegraph.tools.shared_models import GrepMatch, GrepMatches
from codegraph.tools.utils.tool_utils import get_project_root, resolve_paths
from codegraph.utils.logging import get_logger

logger = get_logger()

app = FastMCP(__name__)


def _process_grep_result(grep_result: str, file_path: str, base_path: Path) -> GrepMatches:
    splitter = re.compile(r"^(\d+)[:\-](.*)$")

    results = grep_result.split("\n--\n")
    grep_matches: list[GrepMatch] = []

    for result in results:
        line_no = 0
        contents: list[str] = []

        for line in result.rstrip("\n").split("\n"):
            re_match = splitter.match(line)
            if not re_match:
                logger.error(f"Could not process grep output: {line}")
                continue

            match_line_no: str = re_match.group(1)
            match_content: str = re_match.group(2)

            line_no = line_no or int(match_line_no)
            contents.append(match_content + "\n")

        assert line_no != 0

        grep_matches.append(
            GrepMatch(
                filepath=Path(file_path).relative_to(base_path).as_posix(),
                line_no=line_no,
                contents=contents,
            )
        )

    return GrepMatches(matches=grep_matches)


def _process_multifile_grep_result(
    grep_result: str, base_path: Path, max_results: int | None = None
) -> GrepMatches:
    splitter = re.compile(r"^(.+)([:\-])(\d+)\2(.*)$")

    results = grep_result.split("\n--\n")
    grep_matches: list[GrepMatch] = []

    if max_results is not None:
        results = results[:max_results]

    for result in results:
        path = ""
        line_no = 0
        contents: list[str] = []

        for line in result.rstrip("\n").split("\n"):
            re_match = splitter.match(line)
            if not re_match:
                logger.error(f"Could not process grep output: {line}")
                continue

            match_path: str = re_match.group(1)  # this should stay consistent
            match_line_no: str = re_match.group(3)
            match_content: str = re_match.group(4)

            assert path == "" or path == match_path  # verify path is consistent

            path = path or match_path
            line_no = line_no or int(match_line_no)
            contents.append(match_content + "\n")

        assert path != ""
        assert line_no != 0

        grep_matches.append(
            GrepMatch(
                filepath=Path(path).relative_to(base_path).as_posix(),
                line_no=line_no,
                contents=contents,
            )
        )

    return GrepMatches(matches=grep_matches)


@app.tool(
    exclude_args=["project_id"],
    description=(
        "Search for a string literal or regular expression match in one or more files within the "
        "codebase. You should attempt to use specific patterns with a small context window to "
        "avoid getting too much context for irrelevant results."
    ),
)
async def grep_file(
    pattern: Annotated[
        str,
        (
            "The pattern to search for. If `use_regex=False`, the value is treated as a plain "
            "string (literal match). Otherwise, it is treated as an extended regular expression ("
            "characters like `+`, `{`, `?` become special regex characters). The values must be "
            r"JSON-safe: escape backslashes (`\` -> `\\`) and escape any quotes inside "
            r'(`"` -> `\"`). Patterns can be single words, phrases, or arbitrary regular '
            "expressions. Try to keep it simple if using `use_regex=True` to avoid misses."
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
        bool,
        (
            "Whether to use string literals for `pattern` or regular expressions. In general, "
            "stick with `use_regex=False` and use simple string literal matches."
        ),
    ] = False,
    ignore_case: Annotated[bool, "Whether to ignore cases when finding matches"] = False,
    max_matches: Annotated[
        int, f"Maximum number of matches to find per file. Max {GREP_MAX_MATCHES}."
    ] = GREP_MAX_MATCHES,
    context_before: Annotated[
        int, f"Number of lines before the match to include. Max {GREP_MAX_CONTEXT}."
    ] = 0,
    context_after: Annotated[
        int, f"Number of lines after the match to include. Max {GREP_MAX_CONTEXT}."
    ] = 0,
    # runtime arguments
    project_id: int = -1,
) -> GrepMatches:
    project_root = get_project_root(project_id)

    # clamp values
    max_matches = min(max_matches, GREP_MAX_MATCHES)
    context_before = min(context_before, GREP_MAX_CONTEXT)
    context_after = min(context_after, GREP_MAX_CONTEXT)

    # build args
    resolved_paths = resolve_paths([path] if isinstance(path, str) else path, project_root)
    args = [
        arg
        for arg in (
            "-n",  # include line numbers
            "-I",  # skip binaries
            "-E" if use_regex else "-F",
            "-i" if ignore_case else None,
            "-m",
            str(max_matches),
            "-B",
            str(context_before),
            "-A",
            str(context_after),
        )
        if arg is not None
    ]
    args.append(pattern)
    args.extend(resolved_paths)

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
        return GrepMatches(matches=[])

    return (
        _process_grep_result(stdout.decode(), resolved_paths[0], project_root)
        if len(resolved_paths) == 1
        else _process_multifile_grep_result(stdout.decode(), project_root)
    )


@app.tool(
    exclude_args=["project_id"],
    description=(
        "Search recursively for a string literal or regular expression match in one or more "
        "directories within the codebase. You should attempt to use specific patterns with a small "
        "context window to avoid getting too much context for irrelevant results."
    ),
)
async def grep_dir(
    pattern: Annotated[
        str,
        (
            "The pattern to search for. If `use_regex=False`, the value is treated as a plain "
            "string (literal match). Otherwise, it is treated as an extended regular expression ("
            "characters like `+`, `{`, `?` become special regex characters). The values must be "
            r"JSON-safe: escape backslashes (`\` -> `\\`) and escape any quotes inside "
            r'(`"` -> `\"`). Patterns can be single words, phrases, or arbitrary regular '
            "expressions. Try to keep it simple if using `use_regex=True` to avoid misses."
        ),
    ],
    path: Annotated[
        str | list[str],
        (
            "Dirpath(s) to search for. These should be directories, not files, and should be "
            "relative to the project root directory or absolute. In general, use `path='.'` to "
            "search within the whole codebase."
        ),
    ],
    use_regex: Annotated[
        bool,
        (
            "Whether to use string literals for `pattern` or regular expressions. In general, "
            "stick with `use_regex=False` and use simple string literal matches."
        ),
    ] = False,
    ignore_case: Annotated[bool, "Whether to ignore cases when finding matches"] = False,
    max_matches: Annotated[
        int, f"Maximum number of matches to find in total. Max {GREP_MAX_MATCHES}."
    ] = GREP_MAX_MATCHES,
    context_before: Annotated[
        int, f"Number of lines before the match to include. Max {GREP_MAX_CONTEXT}."
    ] = 0,
    context_after: Annotated[
        int, f"Number of lines after the match to include. Max {GREP_MAX_CONTEXT}."
    ] = 0,
    exclude_dir: Annotated[
        str | list[str] | None,
        (
            "Glob pattern for directories to skip. E.g., `exclude_dir=['.*', 'abc']` will skip "
            "hidden directories and the `abc` directory. Ignored if `None`"
        ),
    ] = ".*",
    include: Annotated[
        str | list[str] | None,
        (
            "Glob pattern for files to include. If this parameter is provided, only files matching "
            "these globs will be included. E.g., `include='*.py'`, it will only include matches "
            "from python files."
        ),
    ] = None,
    exclude: Annotated[
        str | list[str] | None,
        (
            "Glob pattern for files to exclude. E.g., `exclude=['secret*','*.cpp']` will exclude "
            "matches in cpp files and files whose filename starts with 'secret'."
        ),
    ] = None,
    # runtime arguments
    project_id: int = -1,
) -> GrepMatches:
    project_root = get_project_root(project_id)

    # clamp values
    max_matches = min(max_matches, GREP_MAX_MATCHES)
    context_before = min(context_before, GREP_MAX_CONTEXT)
    context_after = min(context_after, GREP_MAX_CONTEXT)

    # build args
    resolved_paths = resolve_paths([path] if isinstance(path, str) else path, project_root)
    args = [
        arg
        for arg in (
            "-n",  # include line numbers
            "-I",  # skip binaries
            "-r",  # recursive
            "-E" if use_regex else "-F",
            "-i" if ignore_case else None,
            "-m",
            str(max_matches),
            "-B",
            str(context_before),
            "-A",
            str(context_after),
        )
        if arg is not None
    ]
    if exclude_dir is not None:
        for i in exclude_dir if isinstance(exclude_dir, list) else [exclude_dir]:
            args.append(f"--exclude-dir={i}")
    if include is not None:
        for i in include if isinstance(include, list) else [include]:
            args.append(f"--include={i}")
    if exclude is not None:
        for i in exclude if isinstance(exclude, list) else [exclude]:
            args.append(f"--exclude={i}")
    args.append(pattern)
    args.extend(resolved_paths)

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
        return GrepMatches(matches=[])

    return _process_multifile_grep_result(stdout.decode(), project_root, max_matches)


if not shutil.which("grep"):
    logger.warning("grep isn't available on this system, grep tools will be disabled")
    grep_file.disable()
    grep_dir.disable()
