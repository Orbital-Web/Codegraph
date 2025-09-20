from pydantic import BaseModel

from codegraph.configs.tools import INTERNAL_TOOL_CALL_ERROR_FLAG


class InternalToolCallError(Exception):
    """An error which when raised should not invoke a retry on the tool call. These are usually
    coding errors, rather than errors resulting from a bad input from an LLM. Since all exceptions
    get converted into a ToolError by FastMCP, we distinguish these errors by checking for the
    `INTERNAL_TOOL_CALL_ERROR_FLAG` string in the error message.
    """

    def __str__(self) -> str:
        return INTERNAL_TOOL_CALL_ERROR_FLAG + super().__str__()


class GrepMatch(BaseModel):
    filepath: str
    line_no: int
    contents: list[str]


class GrepMatches(BaseModel):
    matches: list[GrepMatch]

    def pretty_print(self) -> str:
        if not self.matches:
            return "No matches found."

        output = ""
        for match in self.matches:
            output += match.filepath + ":\n"

            digits = len(str(match.line_no + len(match.contents) - 1))
            for line_no, line in enumerate(match.contents, match.line_no):
                output += f"{str(line_no).ljust(digits)}: {line}"
            output += "\n"

        return output


class FileContent(BaseModel):
    line_no: int
    contents: list[str]

    def pretty_print(self) -> str:
        output = ""
        digits = len(str(self.line_no + len(self.contents) - 1))
        for line_no, line in enumerate(self.contents, self.line_no):
            output += f"{str(line_no).ljust(digits)}: {line}"

        return output


class DirContent(BaseModel):
    contents: list[str]
    untruncated_total_results: int

    def pretty_print(self) -> str:
        return (
            f"Total files and directories: {self.untruncated_total_results}\nContents: "
            + ", ".join(self.contents)
            + (", ..." if len(self.contents) < self.untruncated_total_results else "")
        )
