import json
from uuid import uuid4

from jsonschema import validate
from langchain_core.callbacks.manager import adispatch_custom_event
from langgraph.types import Send
from openai.types.chat import ChatCompletionToolParam

from codegraph.agent.deep_research.models import ToolCallFormat
from codegraph.agent.deep_research.states import AgentState, AgentStep
from codegraph.agent.llm.chat_llm import LLM
from codegraph.agent.llm.models import (
    BaseMessage,
    ToolCall,
    ToolChoice,
    UserMessage,
)
from codegraph.agent.llm.utils import ainvoke_llm_json
from codegraph.agent.models import StreamEvent
from codegraph.agent.prompts.deep_research_prompts import (
    CHOOSE_TOOL_NO_TC_PROMPT,
    CHOOSE_TOOL_PREVIOUS_ATTEMPT_CLAUSE,
    CHOOSE_TOOL_PROMPT,
    PARALLEL_TOOL_CLAUSE,
)
from codegraph.agent.prompts.prompt_utils import format_tools
from codegraph.configs.llm import MAX_LLM_RETRIES


async def _try_choose_tool_no_tc(
    llm: LLM,
    tools: list[ChatCompletionToolParam],
    history: list[BaseMessage],
    current_iteration: int,
    remaining_iteration: int,
) -> ToolCall:
    # TODO: revisit, maybe use history and/or system prompt
    tool_specs = format_tools(tools)
    previous_attempt_clause = ""

    for _ in range(MAX_LLM_RETRIES):
        choose_tool_no_tc_prompt = CHOOSE_TOOL_NO_TC_PROMPT.build(
            current_iteration=str(current_iteration),
            remaining_iteration=(
                f"the next {remaining_iteration} steps or earlier"
                if remaining_iteration > 1
                else "this step"
            ),
            tool_specs=tool_specs,
            previous_attempt_clause=previous_attempt_clause,
        )
        llm_tool_call: ToolCallFormat | None = None
        try:
            llm_tool_call = await ainvoke_llm_json(
                llm,
                [*history, UserMessage(content=choose_tool_no_tc_prompt)],
                ToolCallFormat,
                timeout=120,
            )
            tool_call_name = llm_tool_call.name
            tool_call_args = llm_tool_call.args

            tool_schema = next(
                (
                    tool["function"]["parameters"]
                    for tool in tools
                    if tool["function"]["name"] == tool_call_name
                ),
                None,
            )
            if tool_schema is None:
                raise ValueError(f"Tool {tool_call_name} is not a valid tool.")

            validate(instance=json.loads(tool_call_args), schema=tool_schema)
        except Exception as e:
            previous_attempt_clause = CHOOSE_TOOL_PREVIOUS_ATTEMPT_CLAUSE.build(
                previous_output=str(llm_tool_call), previous_error=str(e)
            )
        else:
            # if no errors were raised, no need to retry
            break
    else:
        # if all attempts failed
        raise RuntimeError("Could not get valid ToolCall from LLM.")

    return ToolCall(name=tool_call_name, args=tool_call_args, id=str(uuid4()), index=0)


async def choose_tools(state: AgentState) -> AgentState:
    """A node which decides which tools to use."""
    await adispatch_custom_event(StreamEvent.CHOOSE_TOOLS, {})

    llm = state["llm"]
    tools = state["tools"]
    history = state["history"]
    use_tool_call = llm.supports_tool_calling()
    use_parallel_tools = llm.supports_parallel_tool_calling()
    current_iteration = state["current_iteration"]
    remaining_iteration = state["max_iteration"] - current_iteration + 1

    if use_tool_call:
        choose_tool_prompt = CHOOSE_TOOL_PROMPT.build(
            parallel_tool_clause=PARALLEL_TOOL_CLAUSE if use_parallel_tools else "",
            current_iteration=str(current_iteration),
            remaining_iteration=(
                f"the next {remaining_iteration} steps or earlier"
                if remaining_iteration > 1
                else "this step"
            ),
        )
        response = await llm.ainvoke(
            [*history, UserMessage(content=choose_tool_prompt)],
            tools=tools,
            tool_choice=ToolChoice.REQUIRED,
            parallel_tool_calls=use_parallel_tools,
            timeout=120,
        )
        tool_calls = response.tool_calls or []

    else:
        tool_calls = [
            await _try_choose_tool_no_tc(
                llm, tools, history, current_iteration, remaining_iteration
            )
        ]

    return {"tool_calls": [tool_call.finalize() for tool_call in tool_calls]}


async def continue_to_tool_call(state: AgentState) -> Send | list[Send]:
    assert state["tool_calls"]

    return [
        Send(AgentStep.CALL_TOOL, {**state, "current_tool": tool_call})
        for tool_call in state["tool_calls"]
    ]
