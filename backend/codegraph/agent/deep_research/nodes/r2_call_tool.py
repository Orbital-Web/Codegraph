from json_schema_to_pydantic import create_model  # type: ignore
from langchain_core.callbacks.manager import adispatch_custom_event
from openai.types.chat import ChatCompletionToolParam

from codegraph.agent.deep_research.models import IterationToolResponse
from codegraph.agent.deep_research.states import AgentState
from codegraph.agent.llm.chat_llm import LLM
from codegraph.agent.llm.models import (
    AssistantMessage,
    BaseMessage,
    ToolCall,
    ToolChoice,
    ToolResponse,
    UserMessage,
)
from codegraph.agent.llm.utils import ainvoke_llm_json
from codegraph.agent.models import StreamEvent
from codegraph.agent.prompts.deep_research_prompts import (
    CALL_TOOL_RETRY_NO_TC_PROMPT,
    CALL_TOOL_RETRY_PROMPT,
)
from codegraph.agent.prompts.prompt_utils import format_tool
from codegraph.configs.llm import MAX_LLM_RETRIES
from codegraph.configs.tools import INTERNAL_TOOL_CALL_ERROR_FLAG, NATIVE_MCP_TOOL_PREFIX
from codegraph.tools.client import MCPClient
from codegraph.utils.logging import get_logger

logger = get_logger()


async def _fix_tool_call(
    llm: LLM,
    history: list[BaseMessage],
    retry_history: list[BaseMessage],
    original_tool_call: ToolCall,
    tool: ChatCompletionToolParam,
    use_tool_call: bool,
) -> ToolCall:
    if use_tool_call:
        response = await llm.ainvoke(
            [*history, *retry_history],
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

    tool_schema = create_model(tool["function"]["parameters"])
    tool_call_args = await ainvoke_llm_json(
        llm, [*history, *retry_history], tool_schema, timeout=120
    )
    return ToolCall(
        name=original_tool_call.name,
        args=tool_call_args.model_dump_json(),
        id=original_tool_call.id,
        index=original_tool_call.index,
    )


async def call_tool(state: AgentState) -> AgentState:
    """A node which calls a tool."""
    tool_call = state["current_tool"]
    await adispatch_custom_event(StreamEvent.TOOL_KICKOFF, tool_call)

    llm = state["llm"]
    use_tool_call = llm.supports_tool_calling()
    client = MCPClient()
    tool = next(
        (tool for tool in state["tools"] if tool["function"]["name"] == tool_call.name),
        None,
    )
    assert tool is not None
    tool_kwargs = (
        {"project_id": state["project_id"]}
        if tool_call.name.startswith(NATIVE_MCP_TOOL_PREFIX + "_")
        else {}
    )
    current_iteration = state["current_iteration"]
    history = state["history"]
    retry_history: list[BaseMessage] = []

    for i in range(MAX_LLM_RETRIES):
        try:
            if i != 0:
                tool_call = await _fix_tool_call(
                    llm, history, retry_history, tool_call, tool, use_tool_call
                )

            tool_result = await client.acall_tool(tool_call, **tool_kwargs)
        except AssertionError:
            # don't retry on AssertionErrors, they're likely coding errors, not LLM errors
            raise
        except Exception as e:
            previous_error = str(e)
            if INTERNAL_TOOL_CALL_ERROR_FLAG in previous_error:
                # don't retry on InternalToolCallError, they're likely coding errors, not LLM errors
                raise

            await adispatch_custom_event(StreamEvent.TOOL_RETRY, tool_call)
            retry_history.append(AssistantMessage(content=tool_call.model_dump_json(indent=4)))
            if use_tool_call:
                retry_prompt = CALL_TOOL_RETRY_PROMPT.build(previous_error=previous_error)
            else:
                retry_prompt = CALL_TOOL_RETRY_NO_TC_PROMPT.build(
                    previous_error=previous_error, tool_spec=format_tool(tool)
                )
            retry_history.append(UserMessage(content=retry_prompt))
        else:
            # if no errors were raised, no need to retry
            break
    else:
        # if all attempts failed
        await adispatch_custom_event(StreamEvent.TOOL_FAILURE, tool_call)
        return {
            "tool_results": [
                IterationToolResponse(
                    iteration=current_iteration,
                    response=ToolResponse(
                        tool_call=tool_call,
                        data=f"Could not call tool {tool_call.name}.",
                        success=False,
                    ),
                )
            ]
        }

    await adispatch_custom_event(StreamEvent.TOOL_COMPLETE, tool_call)
    return {
        "tool_results": [IterationToolResponse(iteration=current_iteration, response=tool_result)]
    }
