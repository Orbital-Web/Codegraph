import asyncio
from typing import cast

from langchain_core.runnables.config import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.typing import ContextT, InputT, OutputT, StateT


async def arun_graph(
    graph: CompiledStateGraph[StateT, ContextT, InputT, OutputT],
    input_state: InputT,
    config: RunnableConfig | None = None,
) -> OutputT:
    return cast(OutputT, await graph.ainvoke(input_state, config=config))


def run_graph(
    graph: CompiledStateGraph[StateT, ContextT, InputT, OutputT],
    input_state: InputT,
    config: RunnableConfig | None = None,
) -> OutputT:
    return asyncio.run(arun_graph(graph, input_state, config))
