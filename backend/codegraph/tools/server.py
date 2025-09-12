import asyncio

from fastmcp import FastMCP

from codegraph.configs.app_configs import NATIVE_MCP_SERVER_HOST, NATIVE_MCP_SERVER_PORT
from codegraph.tools.search.grep_search_tool import app as grep_search_app

app = FastMCP("Codegraph MCP Server")


async def setup() -> None:
    prefix = "cg"
    await app.import_server(grep_search_app, prefix=prefix)


if __name__ == "__main__":
    asyncio.run(setup())
    app.run(transport="http", host=NATIVE_MCP_SERVER_HOST, port=NATIVE_MCP_SERVER_PORT)
