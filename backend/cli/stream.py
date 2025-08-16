import difflib
from pathlib import Path
from colorama import Fore, Style
from typing import Iterable, Generator


def _format_code(code_block: str, project_root: Path, file_path: Path) -> str:
    """
    Formats a code block in the same format as GitHub diffs, using color.
    """
    new_lines = code_block.splitlines()
    old_lines: list[str] = []

    # read old lines
    absolute_file_path = project_root / file_path
    existing_path: Path | None = None
    if absolute_file_path.exists():
        existing_path = absolute_file_path
    elif file_path.exists():
        existing_path = file_path

    if existing_path:
        with open(existing_path, "r", encoding="utf-8") as f:
            old_lines = f.read().splitlines()

    diff = difflib.ndiff(old_lines, new_lines)

    formatted = ""
    for line in diff:
        if line.startswith("+ "):
            formatted += Fore.GREEN + line[2:] + Style.RESET_ALL + "\n"
        elif line.startswith("- "):
            formatted += Fore.RED + line[2:] + Style.RESET_ALL + "\n"
        elif line.startswith("? "):
            # ignore
            continue
        else:
            formatted += line[2:] + "\n"

    return formatted


def stream_with_code_format(
    project_root: Path, stream: Iterable[str]
) -> Generator[str, None, None]:
    """
    Stream text with code diff support. Assumes the line immediately before the start of
    a code block contains the path to the file being edited.
    """
    buffer = ""
    in_code_block = False
    code_buffer = ""
    file_path = ""

    for chunk in stream:
        buffer += chunk

        # wait until newline
        if "\n" not in chunk:
            continue

        # get complete lines and the rest as buffer
        lines = buffer.splitlines(keepends=True)
        if "\n" not in lines[-1]:
            buffer = lines.pop()
        else:
            buffer = ""

        # process each complete line
        for line in lines:
            # handle code block start/end
            if line.startswith("```"):
                if in_code_block:
                    yield _format_code(code_buffer, project_root, Path(file_path))
                    code_buffer = ""
                in_code_block = not in_code_block
                yield line
                continue

            # if inside code block, save text in code buffer
            if in_code_block:
                code_buffer += line
                continue

            # not in code block, stream and save current line as it may be a filepath
            file_path = line.strip()
            yield line

    # handle left over buffer (+1 iteration)
    if buffer:
        # we know buffer contains no newline as it is leftover
        if buffer.startswith("```"):
            if in_code_block:
                yield _format_code(code_buffer, project_root, Path(file_path))
                code_buffer = ""
            in_code_block = not in_code_block
            yield buffer
        elif in_code_block:
            code_buffer += buffer
        else:
            # no need to store filepath as this is the end of the stream
            yield buffer
        buffer = ""

    # handle any left over code
    if in_code_block:
        yield _format_code(code_buffer, project_root, Path(file_path))
        code_buffer = ""
        yield "```\n"

    # all buffers should be empty
    assert code_buffer == "" and buffer == ""
