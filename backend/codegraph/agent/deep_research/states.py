import operator
from enum import Enum
from pathlib import Path
from typing import Annotated

from typing_extensions import TypedDict

from codegraph.agent.llm.models import ToolCall, ToolResponse


class AgentStep(str, Enum):
    # plan
    ANALYZE_INTENT = "analyze_intent"
    GENERATE_PLAN = "generate_plan"
    # repeat
    CHOOSE_TOOLS = "choose_tool"
    CALL_TOOL = "call_tool"
    PLAN_NEXT = "plan_next"
    # close
    RESPOND = "respond"


class AgentInput(TypedDict):
    project_id: int
    user_query: str


class AgentState(AgentInput, total=False):
    # analyze_intent
    overarching_goal: str
    # generate_plan
    overarching_plan: str

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


class AgentOutput(TypedDict):
    pass
