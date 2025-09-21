from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from codegraph.agent.deep_research.nodes.a1_analyze import analyze_intent, continue_or_exit
from codegraph.agent.deep_research.nodes.c1_respond import respond
from codegraph.agent.deep_research.nodes.r1_choose_tools import choose_tools, continue_to_tool_call
from codegraph.agent.deep_research.nodes.r2_call_tool import call_tool
from codegraph.agent.deep_research.nodes.r3_plan_next import complete_or_iterate, plan_next
from codegraph.agent.deep_research.states import AgentInput, AgentOutput, AgentState, AgentStep


def build_graph() -> CompiledStateGraph[AgentState, None, AgentInput, AgentOutput]:
    graph = StateGraph(AgentState, input_schema=AgentInput, output_schema=AgentOutput)

    graph.add_node(AgentStep.ANALYZE_INTENT, analyze_intent)
    graph.add_node(AgentStep.CHOOSE_TOOLS, choose_tools)
    graph.add_node(AgentStep.CALL_TOOL, call_tool)
    graph.add_node(AgentStep.PLAN_NEXT, plan_next)
    graph.add_node(AgentStep.RESPOND, respond)

    graph.add_edge(START, AgentStep.ANALYZE_INTENT)
    graph.add_conditional_edges(
        AgentStep.ANALYZE_INTENT, continue_or_exit, [AgentStep.CHOOSE_TOOLS, AgentStep.RESPOND]
    )
    graph.add_conditional_edges(
        AgentStep.CHOOSE_TOOLS, continue_to_tool_call, [AgentStep.CALL_TOOL]
    )
    graph.add_edge(AgentStep.CALL_TOOL, AgentStep.PLAN_NEXT)
    graph.add_conditional_edges(
        AgentStep.PLAN_NEXT, complete_or_iterate, [AgentStep.RESPOND, AgentStep.CHOOSE_TOOLS]
    )
    graph.add_edge(AgentStep.RESPOND, END)

    return graph.compile()
