from codegraph.agent.deep_research.states import AgentState, AgentStep
from codegraph.agent.llm.models import SystemMessage
from codegraph.agent.prompts.deep_research_prompts import (
    ANALYSIS_EXIT_KEYWORD,
    INTENT_ANALYSIS_PROMPT,
)
from codegraph.agent.prompts.prompt_utils import summarize_tools
from codegraph.tools.client import MCPClient


async def analyze_intent(state: AgentState) -> AgentState:
    """A node which analyzes the user intent and generates a plan."""
    llm = state["llm"]
    client = MCPClient()

    tools = await client.alist_tools()
    tool_summaries = summarize_tools(tools)

    intent_analysis_prompt = INTENT_ANALYSIS_PROMPT.build(
        user_prompt=state["user_prompt"], tool_summaries=tool_summaries
    )
    response = await llm.ainvoke(
        [SystemMessage(content=intent_analysis_prompt)], max_tokens=1000, timeout=120
    )

    analysis_result = response.content.strip()
    if analysis_result.startswith(ANALYSIS_EXIT_KEYWORD):
        return {
            "tools": tools,
            "complete": True,
            "completion_reason": analysis_result[len(ANALYSIS_EXIT_KEYWORD) :].strip(),
        }

    return {"complete": False, "tools": tools, "analysis_result": analysis_result}


async def continue_or_exit(state: AgentState) -> AgentStep:
    if state["complete"]:
        return AgentStep.RESPOND
    return AgentStep.CHOOSE_TOOLS
