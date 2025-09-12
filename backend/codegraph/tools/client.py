# TODO: create test cases for MCP (and probably a fixture to start up the native server)
import asyncio
import json
from pathlib import Path
from time import monotonic, sleep
from typing import Any

from fastmcp import Client
from mcp.types import Tool

from codegraph.agent.llm.models import ToolCall
from codegraph.configs.app_configs import READINESS_INTERVAL, READINESS_TIMEOUT
from codegraph.utils.logging import get_logger

logger = get_logger()

DEFAULT_CONFIG_PATH = Path(__file__).parents[3] / ".vscode" / "mcp_config.json"


class MCPClient:
    """A class for communicating with the configured MCP servers."""

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH):
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.client = Client(self.config)

    async def aping(self) -> bool:
        async with self.client:
            return await self.client.ping()

    async def alist_tools(self) -> list[Tool]:
        async with self.client:
            return await self.client.list_tools()

    async def acall_tool(self, tool_call: ToolCall) -> Any:
        async with self.client:
            return await self.client.call_tool(tool_call.name, tool_call.arguments)

    def list_tools(self) -> list[Tool]:
        return asyncio.run(self.alist_tools())

    def ping(self) -> bool:
        return asyncio.run(self.aping())

    def call_tool(self, tool_call: ToolCall) -> Any:
        return asyncio.run(self.acall_tool(tool_call))


# TODO: call me in test cases
def wait_for_mcp_servers() -> bool:
    logger.info("MCP Server: readiness probe starting")

    mcp_client = MCPClient()
    start_time = monotonic()
    ready = False

    while True:
        try:
            if mcp_client.ping():
                ready = True
                break
        except Exception:
            pass

        elapsed = monotonic() - start_time
        if elapsed > READINESS_TIMEOUT:
            break

        logger.warning(
            f"MCP Server: readiness probe ongoing, elapsed: {elapsed:.1f}s "
            f"timeout={READINESS_TIMEOUT:.1f}s)"
        )
        sleep(READINESS_INTERVAL)

    if not ready:
        logger.error(f"MCP Server: readiness probe did not succeed in {READINESS_TIMEOUT}")
        return False

    logger.info(f"MCP Server: readiness probe succeeded")
    return True
