from codegraph.agent.deep_research.states import AgentState, AgentStep


async def plan_next(state: AgentState) -> AgentState:
    return {
        "project_id": state["project_id"],
        "user_query": state["user_query"],
    }


async def complete_or_iterate(state: AgentState) -> AgentStep:
    if state["complete"]:
        return AgentStep.RESPOND
    return AgentStep.CHOOSE_TOOLS
