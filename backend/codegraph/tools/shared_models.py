class ToolHiddenArgError(Exception):
    """An error that is raised when a tool is called without the appropriate hidden tool arguments.
    These will get converted into ToolError by FastMCP, but should be used to signal that an error
    is caused by the use of the tool by the developer, not the LLM calling it."""
