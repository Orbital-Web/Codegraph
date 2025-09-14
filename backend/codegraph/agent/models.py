from enum import Enum

from pydantic import BaseModel


class StreamEvent(str, Enum):
    GRAPH_START = "graph_start"
    LLM_STREAM = "llm_stream"  # TODO: use
    LLM_STREAM_REASON = "llm_stream_reason"
    CHOOSE_TOOLS = "choose_tools"
    TOOL_KICKOFF = "tool_kickoff"  # TODO: use
    GRAPH_END = "graph_end"  # TODO: use


ALL_STREAM_EVENTS = [event.value for event in StreamEvent]


class ToolCallFormat(BaseModel):
    name: str
    args: str
