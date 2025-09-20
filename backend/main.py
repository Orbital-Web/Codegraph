# FIXME: temporary debug main.py
import asyncio
import warnings
from pathlib import Path

from langchain_core.runnables.config import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.typing import ContextT, InputT, OutputT, StateT

from codegraph.agent.deep_research.graph import build_graph
from codegraph.agent.deep_research.states import AgentInput
from codegraph.agent.graph_runner import astream_graph
from codegraph.agent.llm.chat_llm import LLM
from codegraph.agent.models import StreamEvent
from codegraph.graph.indexing.pipeline import create_project, run_indexing
from tests.integration.reset import reset_all

warnings.filterwarnings("ignore", category=DeprecationWarning)  # needed for litellm warnings


def run_graph(
    graph: CompiledStateGraph[StateT, ContextT, InputT, OutputT],
    input_state: InputT,
    config: RunnableConfig | None = None,
) -> None:
    async def _arun_graph(
        graph: CompiledStateGraph[StateT, ContextT, InputT, OutputT],
        input_state: InputT,
        config: RunnableConfig | None = None,
    ) -> None:
        was_streaming = False
        async for event, data in astream_graph(graph, input_state, config):
            if event == StreamEvent.LLM_STREAM_REASON or event == StreamEvent.LLM_STREAM:
                print(data.content, end="")
                was_streaming = True
            else:
                if was_streaming:
                    print("\n\n")
                    was_streaming = False

                if event == StreamEvent.GRAPH_START:
                    print("Analyzing user intent...")
                elif event == StreamEvent.CHOOSE_TOOLS:
                    print("Choosing tools to call...")
                elif event == StreamEvent.TOOL_KICKOFF:
                    print(f"Running tool `{data.name}`...")
                elif event == StreamEvent.TOOL_RETRY:
                    print(f"Retrying tool `{data.name}`")
                elif event == StreamEvent.TOOL_COMPLETE:
                    print(f"Finished running tool `{data.name}`")
                elif event == StreamEvent.TOOL_FAILURE:
                    print(f"Failed to run tool `{data.name}`")
                else:
                    print("")

    asyncio.run(_arun_graph(graph, input_state, config))


# index codebase
reset_all()
project_name = "test project"
project_root = Path(__file__).parent
project_id = create_project(project_name, project_root)
run_indexing(project_id)


llm = LLM()
user_prompt = input("What would you like to do today?: ")

graph_input: AgentInput = {
    "llm": llm,
    "project_id": 1,
    "user_prompt": user_prompt,
    "max_iteration": 5,
}

graph = build_graph()
run_graph(graph, graph_input)
