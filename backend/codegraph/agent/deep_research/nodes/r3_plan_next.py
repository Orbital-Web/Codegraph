from langchain_core.callbacks.manager import adispatch_custom_event

from codegraph.agent.deep_research.states import AgentState, AgentStep
from codegraph.agent.llm.models import (
    AssistantMessage,
    BaseMessage,
    MessageType,
    UserMessage,
)
from codegraph.agent.models import StreamEvent
from codegraph.agent.prompts.deep_research_prompts import (
    PLAN_CONTINUE_KEYWORD,
    PLAN_END_KEYWORD,
    PLAN_FORCE_TERMINATE_PROMPT,
    PLAN_NEXT_PROMPT,
)
from codegraph.agent.prompts.prompt_utils import format_tool_response, summarize_tools
from codegraph.utils.logging import get_logger

logger = get_logger()


async def plan_next(state: AgentState) -> AgentState:
    """A node which decides whether to continue or reiterate."""
    # TODO: build summary of iteration and decide whether to continue or not
    # make sure to include the tools in the context
    # add them to history. If remaining iteration is 0, add a fake aimessage about that
    llm = state["llm"]
    tools = state["tools"]
    history = state["history"]
    current_iteration = state["current_iteration"]
    tool_responses = [
        format_tool_response(response.response)
        for response in state["tool_results"]
        if response.iteration == current_iteration
    ]

    next_plan_prompt = PLAN_NEXT_PROMPT.build(
        tool_responses="\n".join(tool_responses), tool_summaries=summarize_tools(tools)
    )
    response: BaseMessage | None = None
    async for chunk in llm.astream(
        [*history, UserMessage(content=next_plan_prompt)], max_tokens=1000, timeout=120
    ):
        await adispatch_custom_event(StreamEvent.LLM_STREAM_REASON, chunk)
        if response is None:
            response = chunk
        else:
            response += chunk

    assert response is not None
    assert response.role == MessageType.ASSISTANT
    history.extend(AssistantMessage(content=tool_response) for tool_response in tool_responses)
    plan_result = response.content.strip("\n- ")

    complete: bool = False
    if plan_result.endswith(PLAN_END_KEYWORD):
        complete = True
    elif not plan_result.endswith(PLAN_CONTINUE_KEYWORD):
        logger.warning(
            f"Plan result did not end with either {PLAN_END_KEYWORD} or "
            f"{PLAN_CONTINUE_KEYWORD}, falling back to continue."
        )

    history.append(AssistantMessage(content=plan_result))
    if current_iteration + 1 == state["max_iteration"] and not complete:
        # if we want to continue, but can't, insert a 'fake' assistant message and force terminate
        history.append(AssistantMessage(content=PLAN_FORCE_TERMINATE_PROMPT))
        complete = True

    return {"history": history, "complete": complete, "current_iteration": current_iteration + 1}


async def complete_or_iterate(state: AgentState) -> AgentStep:
    if state["complete"]:
        return AgentStep.RESPOND
    return AgentStep.CHOOSE_TOOLS
