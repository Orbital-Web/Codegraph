import os
from typing import Annotated

from fastmcp import FastMCP

from codegraph.configs.tools import FILE_MAX_READ_LINES, LIST_DIR_MAX_NUM_CONTENTS
from codegraph.tools.shared_models import DirContent, FileContent
from codegraph.tools.utils.tool_utils import get_project_root, resolve_paths
from codegraph.utils.logging import get_logger

logger = get_logger()

app = FastMCP(__name__)


@app.tool(
    exclude_args=["project_id"],
    description="Reads the content of one or more files within the codebase.",
)
async def read_file(
    path: Annotated[str, "Filepath to read the contents of."],
    start_line: Annotated[int, "Line number to read from, 1-indexed."] = 1,
    max_lines: Annotated[
        int, f"Number of lines to read. Max {FILE_MAX_READ_LINES}."
    ] = FILE_MAX_READ_LINES,
    # runtime arguments
    project_id: int = -1,
) -> FileContent:
    project_root = get_project_root(project_id)

    # clamp values
    max_lines = min(max_lines, FILE_MAX_READ_LINES)

    resolved_path = resolve_paths([path], project_root)[0]
    contents: list[str] = []
    with open(resolved_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line_num >= start_line + max_lines:
                break
            if line_num >= start_line:
                contents.append(line)

    return FileContent(line_no=start_line, contents=contents)


@app.tool(
    exclude_args=["project_id"],
    description=(
        "Lists the contents of a directory. Useful for understanding the file structure of the "
        "codebase before diving deeper into specific files or tools (like the grep_dir tool). "
        f"If the number of results exceeds {LIST_DIR_MAX_NUM_CONTENTS}, the output will be "
        "truncated."
    ),
)
async def list_dir(
    path: Annotated[str, "Dirpath to list the contents of."],
    # runtime arguments
    project_id: int = -1,
) -> DirContent:
    project_root = get_project_root(project_id)
    resolved_path = resolve_paths([path], project_root)[0]
    ls = os.listdir(resolved_path)

    return DirContent(contents=ls[:LIST_DIR_MAX_NUM_CONTENTS], untruncated_total_results=len(ls))


# TODO: edit_file
# TODO: find_file (fuzzymatch)
