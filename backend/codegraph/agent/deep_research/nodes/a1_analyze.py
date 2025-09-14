from typing import cast

from langchain_core.callbacks.manager import adispatch_custom_event

from codegraph.agent.deep_research.states import AgentState, AgentStep
from codegraph.agent.llm.models import BaseMessage, SystemMessage
from codegraph.agent.models import StreamEvent
from codegraph.agent.prompts.deep_research_prompts import (
    ANALYSIS_EXIT_KEYWORD,
    INTENT_ANALYSIS_PROMPT,
)
from codegraph.agent.prompts.prompt_utils import summarize_tools
from codegraph.tools.client import MCPClient


async def analyze_intent(state: AgentState) -> AgentState:
    """A node which analyzes the user intent and generates a plan."""
    await adispatch_custom_event(StreamEvent.GRAPH_START, {})

    llm = state["llm"]
    client = MCPClient()
    tools = await client.alist_openai_tools()
    tool_summaries = summarize_tools(tools)

    intent_analysis_prompt = INTENT_ANALYSIS_PROMPT.build(
        user_prompt=state["user_prompt"], tool_summaries=tool_summaries
    )
    response: BaseMessage | None = None
    async for chunk in llm.astream(
        [SystemMessage(content=intent_analysis_prompt)], max_tokens=1000, timeout=120
    ):
        await adispatch_custom_event(StreamEvent.LLM_STREAM_REASON, chunk)
        if response is None:
            response = chunk
        else:
            response += chunk

    analysis_result = cast(BaseMessage, response).content.strip()
    if analysis_result.startswith(ANALYSIS_EXIT_KEYWORD):
        return {
            "tools": tools,
            "complete": True,
            "completion_reason": analysis_result[len(ANALYSIS_EXIT_KEYWORD) :].strip(),
            "current_iteration": 1,
        }

    return {
        "complete": False,
        "tools": tools,
        "analysis_result": analysis_result,
        "current_iteration": 1,
    }


async def continue_or_exit(state: AgentState) -> AgentStep:
    if state["complete"]:
        return AgentStep.RESPOND
    return AgentStep.CHOOSE_TOOLS
