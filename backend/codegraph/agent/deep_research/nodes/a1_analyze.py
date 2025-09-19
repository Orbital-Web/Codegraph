from langchain_core.callbacks.manager import adispatch_custom_event

from codegraph.agent.deep_research.states import AgentState, AgentStep
from codegraph.agent.llm.models import (
    AssistantMessage,
    BaseMessage,
    MessageType,
    SystemMessage,
    UserMessage,
)
from codegraph.agent.models import StreamEvent
from codegraph.agent.prompts.deep_research_prompts import (
    AGENT_SYSTEM_PROMPT,
    ANALYSIS_EXIT_KEYWORD,
    INTENT_ANALYSIS_PROMPT,
)
from codegraph.agent.prompts.prompt_utils import summarize_tools
from codegraph.tools.client import MCPClient


async def analyze_intent(state: AgentState) -> AgentState:
    """A node which analyzes the user intent and generates a plan."""
    await adispatch_custom_event(StreamEvent.GRAPH_START, {})

    user_prompt = state["user_prompt"]
    llm = state["llm"]
    client = MCPClient()
    tools = await client.alist_openai_tools()
    history: list[BaseMessage] = [SystemMessage(content=AGENT_SYSTEM_PROMPT)]

    intent_analysis_prompt = INTENT_ANALYSIS_PROMPT.build(
        user_prompt=user_prompt, tool_summaries=summarize_tools(tools)
    )
    response: BaseMessage | None = None
    async for chunk in llm.astream(
        [*history, UserMessage(content=intent_analysis_prompt)], max_tokens=1000, timeout=120
    ):
        await adispatch_custom_event(StreamEvent.LLM_STREAM_REASON, chunk)
        if response is None:
            response = chunk
        else:
            response += chunk

    assert response is not None
    assert response.role == MessageType.ASSISTANT
    history.append(UserMessage(content=user_prompt))
    analysis_result = response.content.strip("\n-")

    if analysis_result.startswith(ANALYSIS_EXIT_KEYWORD):
        history.append(
            AssistantMessage(content=analysis_result[len(ANALYSIS_EXIT_KEYWORD) :].strip())
        )
        complete = True
    else:
        history.append(AssistantMessage(content=analysis_result))
        complete = False

    return {"tools": tools, "history": history, "current_iteration": 1, "complete": complete}


async def continue_or_exit(state: AgentState) -> AgentStep:
    if state["complete"]:
        return AgentStep.RESPOND
    return AgentStep.CHOOSE_TOOLS
