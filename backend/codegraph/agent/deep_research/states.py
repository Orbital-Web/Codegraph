import operator
from enum import Enum
from pathlib import Path
from typing import Annotated

from mcp.types import Tool
from typing_extensions import TypedDict

from codegraph.agent.llm.chat_llm import LLM
from codegraph.agent.llm.models import ToolCall, ToolResponse


class AgentStep(str, Enum):
    # analyze
    ANALYZE_INTENT = "analyze_intent"
    # repeat
    CHOOSE_TOOLS = "choose_tool"
    CALL_TOOL = "call_tool"
    PLAN_NEXT = "plan_next"
    # close
    RESPOND = "respond"


class AgentInput(TypedDict):
    project_id: int
    user_prompt: str
    llm: LLM


class AgentState(TypedDict, total=False):
    # input, should not be modified
    project_id: int
    user_prompt: str
    llm: LLM

    # analyze_intent
    tools: list[Tool]
    analysis_result: str

    # choose_tool
    current_iteration: int
    current_plan: str
    tool_calls: list[ToolCall]
    # call_tool
    current_tool: ToolCall
    tool_results: Annotated[list[ToolResponse], operator.add]
    generated_codes: Annotated[list[tuple[Path, str]], operator.add]
    # plan_next
    iteration_summaries: Annotated[list[str], operator.add]
    complete: bool
    completion_reason: str


class AgentOutput(TypedDict):
    # TODO: add response text + generated code, then write a cli func to print this nicely
    pass
