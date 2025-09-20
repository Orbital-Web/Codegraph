from langchain_core.callbacks.manager import adispatch_custom_event

from codegraph.agent.deep_research.states import AgentOutput, AgentState
from codegraph.agent.llm.models import AssistantMessage, UserMessage
from codegraph.agent.models import StreamEvent
from codegraph.agent.prompts.deep_research_prompts import FINAL_RESPONSE_PROMPT


async def respond(state: AgentState) -> AgentOutput:
    """A node for generating the final response to the user."""
    llm = state["llm"]
    history = state["history"]

    final_response_prompt = FINAL_RESPONSE_PROMPT
    response: AssistantMessage | None = None
    async for chunk in llm.astream(
        [*history, UserMessage(content=final_response_prompt)], max_tokens=3000, timeout=240
    ):
        await adispatch_custom_event(StreamEvent.LLM_STREAM, chunk)
        if response is None:
            response = chunk
        else:
            response += chunk

    await adispatch_custom_event(StreamEvent.GRAPH_END, {})
    return {}
