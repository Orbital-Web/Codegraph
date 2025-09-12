import asyncio

from fastmcp import FastMCP

from codegraph.configs.app_configs import (
    NATIVE_MCP_SERVER_HOST,
    NATIVE_MCP_SERVER_PORT,
    NATIVE_MCP_TOOL_PREFIX,
)
from codegraph.tools.search.grep_search_tool import app as grep_search_app
from codegraph.utils.configuration import initialize_and_wait_for_services

app = FastMCP("Codegraph MCP Server")


async def setup() -> None:
    await app.import_server(grep_search_app, prefix=NATIVE_MCP_TOOL_PREFIX)


if __name__ == "__main__":
    ready = initialize_and_wait_for_services()
    if not ready:
        raise RuntimeError("Failed to initialize services")

    asyncio.run(setup())
    app.run(transport="http", host=NATIVE_MCP_SERVER_HOST, port=NATIVE_MCP_SERVER_PORT)
