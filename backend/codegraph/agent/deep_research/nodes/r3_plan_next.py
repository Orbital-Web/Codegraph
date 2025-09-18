from codegraph.agent.deep_research.states import AgentState, AgentStep


async def plan_next(state: AgentState) -> AgentState:
    # TODO: build summary of iteration and decide whether to continue or not
    # make sure to include the tools in the context
    # add them to history. If remaining iteration is 0, add a fake aimessage about that
    return {}


async def complete_or_iterate(state: AgentState) -> AgentStep:
    if state["complete"]:
        return AgentStep.RESPOND
    return AgentStep.CHOOSE_TOOLS
