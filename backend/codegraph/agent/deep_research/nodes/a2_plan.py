from codegraph.agent.deep_research.states import AgentState


async def generate_plan(state: AgentState) -> AgentState:
    return {
        "project_id": state["project_id"],
        "user_query": state["user_query"],
    }
