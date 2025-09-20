from pydantic import BaseModel

from codegraph.configs.app_configs import INTERNAL_TOOL_CALL_ERROR_FLAG


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
    content: str


class GrepMatches(BaseModel):
    matches: list[GrepMatch]
