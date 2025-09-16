import json
from enum import Enum
from typing import Any, Literal, cast
from uuid import uuid4

from pydantic import BaseModel
from typing_extensions import TypedDict


class LLMValidationInfo(TypedDict, total=False):
    model_name_suggestions: list[str]
    missing_keys: list[str]
    invalid_key: bool


class LLMException(Exception):
    pass


class MessageType(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ReasoningEffort(str, Enum):
    NONE = "none"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DEFAULT = "default"


class ToolChoice(str, Enum):
    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"


class ToolCall(BaseModel):
    name: str
    args: str
    id: str
    index: int

    @property
    def arguments(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.args))

    @classmethod
    def build(cls, tool_name: str, tool_args: dict[str, Any]) -> "ToolCall":
        return ToolCall(name=tool_name, args=json.dumps(tool_args), id=str(uuid4()), index=0)

    def finalize(self) -> "ToolCall":
        """Validates the tool call and sets `id` if unset, as some models may return empty strings
        for the fields.
        """
        if not self.name:
            raise ValueError("Name cannot be empty")
        if not self.id:
            self.id = str(uuid4())
        return self


class ToolResponse(BaseModel):
    id: str
    data: Any
    success: bool = True


class BaseMessage(BaseModel):
    role: MessageType
    content: str

    reasoning_content: str | None = None
    tool_calls: list[ToolCall] | None = None

    def to_dict(self) -> dict[str, Any]:
        message_dict: dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.tool_calls:
            message_dict["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "function": {
                        "name": tool_call.name,
                        "arguments": tool_call.args,
                    },
                    "type": "function",
                }
                for tool_call in self.tool_calls
            ]
        return message_dict

    def __add__(self, other: "BaseMessage") -> "BaseMessage":
        assert self.role == other.role

        merged_tool_calls = {tool.index: tool.model_copy() for tool in self.tool_calls or []}
        for tool in other.tool_calls or []:
            if tool.index in merged_tool_calls:
                # name and id usually only provided once in a stream of message chunks
                merged_tool_calls[tool.index].name = tool.name or merged_tool_calls[tool.index].name
                merged_tool_calls[tool.index].args += tool.args
                merged_tool_calls[tool.index].id = tool.id or merged_tool_calls[tool.index].id
            else:
                merged_tool_calls[tool.index] = tool.model_copy()

        return BaseMessage(
            role=self.role,
            content=self.content + other.content,
            reasoning_content=(
                (self.reasoning_content or "") + (other.reasoning_content or "") or None
            ),
            tool_calls=list(merged_tool_calls.values()) or None,
        )


class SystemMessage(BaseMessage):
    role: Literal[MessageType.SYSTEM] = MessageType.SYSTEM


class UserMessage(BaseMessage):
    role: Literal[MessageType.USER] = MessageType.USER


class AssistantMessage(BaseMessage):
    role: Literal[MessageType.ASSISTANT] = MessageType.ASSISTANT
