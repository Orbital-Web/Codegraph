from langgraph.types import Send

from codegraph.agent.deep_research.states import AgentState, AgentStep


async def choose_tools(state: AgentState) -> AgentState:
    # TODO: call tool_call.finalize() for the generated tool calls
    return {}


async def continue_to_tool_call(state: AgentState) -> Send | list[Send]:
    if not state["tool_calls"]:
        return Send(
            AgentStep.RESPOND, {"complete": True, "completion_reason": "no tools were called"}
        )

    return [
        Send(AgentStep.CALL_TOOL, {"current_tool": tool_call}) for tool_call in state["tool_calls"]
    ]
