import json

from json_schema_to_pydantic import create_model  # type: ignore
from langchain_core.callbacks.manager import adispatch_custom_event
from openai.types.chat import ChatCompletionToolParam

from codegraph.agent.deep_research.models import IterationToolResponse
from codegraph.agent.deep_research.states import AgentState
from codegraph.agent.llm.chat_llm import LLM
from codegraph.agent.llm.models import ToolCall, ToolChoice, ToolResponse, UserMessage
from codegraph.agent.llm.utils import ainvoke_llm_json
from codegraph.agent.models import StreamEvent
from codegraph.agent.prompts.deep_research_prompts import (
    CALL_TOOL_ON_FAIL_NO_TC_PROMPT,
    CALL_TOOL_ON_FAIL_PROMPT,
)
from codegraph.agent.prompts.prompt_utils import format_tool
from codegraph.configs.app_configs import INTERNAL_TOOL_CALL_ERROR_FLAG, NATIVE_MCP_TOOL_PREFIX
from codegraph.configs.llm import MAX_LLM_RETRIES
from codegraph.tools.client import MCPClient
from codegraph.utils.logging import get_logger

logger = get_logger()


async def _fix_tool_call(
    llm: LLM,
    original_tool_call: ToolCall,
    tool: ChatCompletionToolParam,
    previous_tool_args: str,
    previous_error: str,
) -> ToolCall:
    # TODO: revisit, maybe use history and/or system prompt
    use_tool_call = llm.supports_tool_calling()

    if use_tool_call:
        fix_tool_call_prompt = CALL_TOOL_ON_FAIL_PROMPT.build(
            previous_tool_args=previous_tool_args, previous_error=previous_error
        )
        response = await llm.ainvoke(
            [UserMessage(content=fix_tool_call_prompt)],
            tools=[tool],
            tool_choice=ToolChoice.REQUIRED,
            parallel_tool_calls=False,
            timeout=120,
        )
        tool_calls = response.tool_calls
        assert tool_calls
        tool_call = tool_calls[0]
        assert tool_call.name == original_tool_call.name
        tool_call.id = original_tool_call.id
        tool_call.index = original_tool_call.index
        return tool_call

    fix_tool_call_prompt = CALL_TOOL_ON_FAIL_NO_TC_PROMPT.build(
        previous_tool_args=previous_tool_args,
        previous_error=previous_error,
        tool_spec=format_tool(tool),
    )
    tool_schema = create_model(tool["function"]["parameters"])
    tool_call_args = await ainvoke_llm_json(
        llm, [UserMessage(content=fix_tool_call_prompt)], tool_schema, timeout=120
    )
    return ToolCall(
        name=original_tool_call.name,
        args=tool_call_args.model_dump_json(),
        id=original_tool_call.id,
        index=original_tool_call.index,
    )


async def call_tool(state: AgentState) -> AgentState:
    tool_call = state["current_tool"]
    await adispatch_custom_event(StreamEvent.TOOL_KICKOFF, tool_call)

    llm = state["llm"]
    client = MCPClient()
    tool = next(
        (tool for tool in state["tools"] if tool["function"]["name"] == tool_call.name),
        None,
    )
    assert tool is not None
    tool_kwargs = (
        {"project_id": state["project_id"]}
        if tool_call.name.startswith(NATIVE_MCP_TOOL_PREFIX)
        else {}
    )
    current_iteration = state["current_iteration"]

    remaining_attempts = MAX_LLM_RETRIES
    while remaining_attempts > 0:
        try:
            tool_result = await client.acall_tool(tool_call, **tool_kwargs)
        except Exception as e:
            remaining_attempts -= 1
            previous_tool_args = json.dumps(tool_call.arguments, indent=4)
            previous_error = str(e)
            if INTERNAL_TOOL_CALL_ERROR_FLAG in previous_error:
                # if it's an InternalToolCallError, raise as these are coding errors
                raise
        else:
            # if no errors were raised, no need to retry
            break

        while remaining_attempts > 0:
            try:
                tool_call = await _fix_tool_call(
                    llm, tool_call, tool, previous_tool_args, previous_error
                )
            except AssertionError:
                # don't ignore AssertionErrors, they're likely a coding error, not an LLM error
                raise
            except Exception:
                remaining_attempts -= 1
            else:
                # if no errors were raised, continue with new tool call
                break
    else:
        # if all attempts failed
        error_msg = f"Could not call tool {tool_call.name}."
        logger.error(error_msg)
        return {
            "tool_results": [
                IterationToolResponse(
                    iteration=current_iteration,
                    response=ToolResponse(id=tool_call.id, data=error_msg, success=False),
                )
            ]
        }

    await adispatch_custom_event(StreamEvent.TOOL_COMPLETE, tool_call)
    return {
        "tool_results": [IterationToolResponse(iteration=current_iteration, response=tool_result)]
    }
