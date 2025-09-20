from enum import Enum


class StreamEvent(str, Enum):
    GRAPH_START = "graph_start"  # {}
    LLM_STREAM = "llm_stream"  # AssistantMessage
    LLM_STREAM_REASON = "llm_stream_reason"  # AssistantMessage
    CHOOSE_TOOLS = "choose_tools"  # {}
    TOOL_KICKOFF = "tool_kickoff"  # ToolCall
    TOOL_RETRY = "tool_retry"  # ToolCall
    TOOL_COMPLETE = "tool_complete"  # ToolCall
    TOOL_FAILURE = "tool_failure"  # ToolCall
    GRAPH_END = "graph_end"  # {}


ALL_STREAM_EVENTS = [event.value for event in StreamEvent]
