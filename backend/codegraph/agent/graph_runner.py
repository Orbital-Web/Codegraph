from typing import Any, AsyncIterator, cast

from langchain_core.runnables.config import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.typing import ContextT, InputT, OutputT, StateT

from codegraph.agent.models import ALL_STREAM_EVENTS, StreamEvent


async def astream_graph(
    graph: CompiledStateGraph[StateT, ContextT, InputT, OutputT],
    input_state: InputT,
    config: RunnableConfig | None = None,
) -> AsyncIterator[tuple[StreamEvent, Any]]:
    """Runs the graph and streams events."""
    async for event in graph.astream_events(input_state, config, include_names=ALL_STREAM_EVENTS):
        event_name = cast(StreamEvent, event["name"])
        event_data = event["data"]
        yield event_name, event_data
