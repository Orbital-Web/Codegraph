from langgraph.types import Send

from codegraph.agent.deep_research.states import AgentState, AgentStep


async def choose_tools(state: AgentState) -> AgentState:
    # TODO: call tool_call.finalize() for the generated tool calls
    return {
        "project_id": state["project_id"],
        "user_query": state["user_query"],
    }


async def continue_to_tool_call(state: AgentState) -> list[Send]:
    return [
        Send(AgentStep.CALL_TOOL, {"current_tool": tool_call}) for tool_call in state["tool_calls"]
    ]
