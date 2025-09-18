import operator
from enum import Enum
from pathlib import Path
from typing import Annotated

from openai.types.chat import ChatCompletionToolParam
from typing_extensions import TypedDict

from codegraph.agent.deep_research.models import IterationToolResponse
from codegraph.agent.llm.chat_llm import LLM
from codegraph.agent.llm.models import BaseMessage, ToolCall


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
    max_iteration: int


class AgentState(TypedDict, total=False):
    # input, should not be modified
    project_id: int
    user_prompt: str
    llm: LLM
    max_iteration: int

    # analyze_intent
    tools: list[ChatCompletionToolParam]
    history: list[BaseMessage]

    # choose_tool
    current_iteration: int
    tool_calls: list[ToolCall]
    # call_tool
    current_tool: ToolCall
    tool_results: Annotated[list[IterationToolResponse], operator.add]
    generated_codes: Annotated[list[tuple[Path, str]], operator.add]  # TODO: fill in call_tool
    # plan_next
    iteration_summaries: Annotated[list[str], operator.add]
    complete: bool


class AgentOutput(TypedDict):
    pass
