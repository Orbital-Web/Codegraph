# mypy: disable-error-code="attr-defined, name-defined"
from typing import Any, AsyncIterator, Iterator, Type, cast

import litellm
from litellm.utils import ChatCompletionDeltaToolCall, Delta
from pydantic import BaseModel
from rapidfuzz import fuzz, process

from codegraph.agent.llm.models import (
    AssistantMessage,
    BaseMessage,
    LLMException,
    LLMValidationInfo,
    ReasoningEffort,
    SystemMessage,
    ToolCall,
    ToolChoice,
    UserMessage,
)
from codegraph.configs.llm import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME
from codegraph.utils.logging import get_logger

logger = get_logger()


class LLM:
    """A thread-safe class for managing LLM completion and streaming."""

    def __init__(
        self,
        model_name: str = LLM_MODEL_NAME,
        api_key: str = LLM_API_KEY,
        api_base: str | None = LLM_API_BASE,
        strict: bool = True,
        validate: bool = True,
    ) -> None:
        """Initializes a litellm-based class for doing chat completions with LLMs.

        Args:
            model_name: The name of the model to use (e.g., `gpt-5`). Defaults to `LLM_MODEL_NAME`.
            api_key: The api key of the model. Defaults to `LLM_API_KEY`.
            api_base: The api endpoint of the model, if not the default API endpoint. Defaults to
                `LLM_API_BASE`.
            strict: Whether to raise an exception if using unsupported arguments for the model
                during completion. Defaults to `True`.
            validate: Whether the validate the `model_name`, `api_key`, `api_base`, and required
                environmental variables for the model. Defaults to `True`.
        """
        if validate and (result := self.validate_llm(model_name, api_key, api_base)) is not None:
            if "model_name_suggestions" in result:
                raise LLMException(
                    f"Unknown model_name `{model_name}`. "
                    f"Do you mean: {result['model_name_suggestions']}"
                )
            elif "missing_keys" in result:
                raise LLMException(f"Missing keys: {result['missing_keys']} in environment")
            elif "invalid_key" in result:
                raise LLMException("Invalid `api_key`")
            else:
                raise LLMException("Could not validate LLM")

        self.model_name = model_name
        self.api_key = api_key
        self.api_base = api_base
        self.strict = strict
        self.supported_params: set[str] = set(
            litellm.get_supported_openai_params(model_name, request_type="chat_completion") or []
        )

    def validate_llm(
        self, model_name: str, api_key: str, api_base: str | None
    ) -> LLMValidationInfo | None:
        """Validates the `model_name`, `api_key`, `api_base`, and environmental variables.
        If `model_name` is not a valid model, it will return a dictionary with suggested model
        names. If there are any missing environmental variables, it will return a dictionary with
        those missing keys. Otherwise, if everything is good, it will return `None`.
        """
        if not model_name:
            return {"model_name_suggestions": sorted(litellm.model_list)}
        if model_name not in litellm.model_list_set:
            suggestions = process.extract(
                model_name, litellm.model_list_set, scorer=fuzz.ratio, limit=5
            )
            return {"model_name_suggestions": [name for name, score, rank in suggestions]}

        result = litellm.validate_environment(model_name, api_key, api_base)
        if not result["keys_in_environment"]:
            return {"missing_keys": result["missing_keys"]}

        if not litellm.check_valid_key(model_name, api_key):
            return {"invalid_key": True}

        return None

    def invoke(
        self,
        messages: list[BaseMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: ToolChoice | None = None,
        parallel_tool_calls: bool | None = None,
        response_schema: Type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
    ) -> BaseMessage:
        response = cast(
            litellm.ModelResponse,
            self._completion(
                messages,
                tools=tools,
                tool_choice=tool_choice,
                parallel_tool_calls=parallel_tool_calls,
                response_format=response_schema,
                reasoning_effort=reasoning_effort,
                timeout=timeout,
                max_tokens=max_tokens,
                stream=False,
            ),
        )
        choice = response.choices[0]
        message = choice.message
        return _convert_litellm_message(message)

    def stream(
        self,
        messages: list[BaseMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: ToolChoice | None = None,
        parallel_tool_calls: bool | None = None,
        response_schema: Type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[BaseMessage]:
        response = cast(
            litellm.CustomStreamWrapper,
            self._completion(
                messages,
                tools=tools,
                tool_choice=tool_choice,
                parallel_tool_calls=parallel_tool_calls,
                response_format=response_schema,
                reasoning_effort=reasoning_effort,
                timeout=timeout,
                max_tokens=max_tokens,
                stream=True,
            ),
        )
        role: str | None = None
        for part in response:
            if not part.choices:
                continue
            choice = part.choices[0]
            delta = choice.delta

            message = _convert_litellm_delta(delta, role)
            role = message.role.value
            yield message

    def _completion(
        self,
        messages: list[BaseMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: ToolChoice | None = None,
        parallel_tool_calls: bool | None = None,
        response_format: Type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> litellm.ModelResponse | litellm.CustomStreamWrapper:
        if not self.strict:
            # if we're not enforcing, raise a warning instead
            provided_args = {
                name
                for name, val in locals().items()
                if val is not None and name not in {"self", "messages", "timeout"}
            }
            if unsupported_args := provided_args - self.supported_params:
                logger.warning(
                    f"Received unsupported arguments {unsupported_args} for model {self.model_name}"
                )

        return litellm.completion(
            model=self.model_name,
            api_key=self.api_key,
            api_base=self.api_base,
            messages=[message.to_dict() for message in messages],
            # tools
            tools=tools,
            tool_choice=tool_choice.value if tool_choice and tools else None,
            parallel_tool_calls=parallel_tool_calls,
            # structured response
            response_format=response_format,
            # model parameters
            reasoning_effort=reasoning_effort.value if reasoning_effort else None,
            # timeout and token constraints
            timeout=timeout,
            max_tokens=max_tokens,
            # behavior
            stream=stream,
            drop_params=not self.strict,  # ignore unsupported operations if not strict
        )

    def supports_tool_calling(self) -> bool:
        return litellm.utils.supports_function_calling(self.model_name)

    def supports_parallel_tool_calling(self) -> bool:
        return litellm.utils.supports_parallel_function_calling(self.model_name)

    def supports_structured_response(self) -> bool:
        return (
            "response_format" in self.supported_params
            and litellm.utils.supports_response_schema(self.model_name)
        )

    async def ainvoke(
        self,
        messages: list[BaseMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: ToolChoice | None = None,
        parallel_tool_calls: bool | None = None,
        response_schema: Type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
    ) -> BaseMessage:
        response = cast(
            litellm.ModelResponse,
            await self._acompletion(
                messages,
                tools=tools,
                tool_choice=tool_choice,
                parallel_tool_calls=parallel_tool_calls,
                response_format=response_schema,
                reasoning_effort=reasoning_effort,
                timeout=timeout,
                max_tokens=max_tokens,
                stream=False,
            ),
        )
        choice = response.choices[0]
        message = choice.message
        return _convert_litellm_message(message)

    async def astream(
        self,
        messages: list[BaseMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: ToolChoice | None = None,
        parallel_tool_calls: bool | None = None,
        response_schema: Type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[BaseMessage]:
        response = cast(
            litellm.CustomStreamWrapper,
            await self._acompletion(
                messages,
                tools=tools,
                tool_choice=tool_choice,
                parallel_tool_calls=parallel_tool_calls,
                response_format=response_schema,
                reasoning_effort=reasoning_effort,
                timeout=timeout,
                max_tokens=max_tokens,
                stream=True,
            ),
        )
        role: str | None = None
        for part in response:
            if not part.choices:
                continue
            choice = part.choices[0]
            delta = choice.delta

            message = _convert_litellm_delta(delta, role)
            role = message.role.value
            yield message

    async def _acompletion(
        self,
        messages: list[BaseMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: ToolChoice | None = None,
        parallel_tool_calls: bool | None = None,
        response_format: Type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> litellm.ModelResponse | litellm.CustomStreamWrapper:
        if not self.strict:
            # if we're not enforcing, raise a warning instead
            provided_args = {
                name
                for name, val in locals().items()
                if val is not None and name not in {"self", "messages", "timeout"}
            }
            if unsupported_args := provided_args - self.supported_params:
                logger.warning(
                    f"Received unsupported arguments {unsupported_args} for model {self.model_name}"
                )

        return await litellm.acompletion(
            model=self.model_name,
            api_key=self.api_key,
            api_base=self.api_base,
            messages=[message.to_dict() for message in messages],
            # tools
            tools=tools,
            tool_choice=tool_choice.value if tool_choice and tools else None,
            parallel_tool_calls=parallel_tool_calls,
            # structured response
            response_format=response_format,
            # model parameters
            reasoning_effort=reasoning_effort.value if reasoning_effort else None,
            # timeout and token constraints
            timeout=timeout,
            max_tokens=max_tokens,
            # behavior
            stream=stream,
            drop_params=not self.strict,  # ignore unsupported operations if not strict
        )


def _convert_litellm_message(message: litellm.Message) -> BaseMessage:
    content = message.content or ""
    tool_calls = cast(
        list[litellm.ChatCompletionMessageToolCall],
        message.tool_calls if hasattr(message, "tool_calls") else None,
    )
    reasoning_content = message.reasoning_content if hasattr(message, "reasoning_content") else None

    if message.role == "assistant" or tool_calls:
        return AssistantMessage(
            content=content,
            reasoning_content=reasoning_content,
            tool_calls=(
                [
                    ToolCall(
                        name=tool_call.function.name or "",
                        args=tool_call.function.arguments,
                        id=tool_call.id,
                        index=index,
                    )
                    for index, tool_call in enumerate(tool_calls)
                ]
                if tool_calls
                else None
            ),
        )
    elif message.role == "user":
        return UserMessage(content=content)
    elif message.role == "system":
        return SystemMessage(content=content)
    else:
        raise ValueError(f"Unknown message role {message.role}")


def _convert_litellm_delta(delta: Delta, default_role: str | None) -> BaseMessage:
    role = delta.role or default_role
    content = delta.content or ""
    tool_calls = cast(list[ChatCompletionDeltaToolCall] | None, delta.tool_calls)
    reasoning_content = delta.reasoning_content if hasattr(delta, "reasoning_content") else None

    if role == "assistant" or tool_calls:
        return AssistantMessage(
            content=content,
            reasoning_content=reasoning_content,
            tool_calls=(
                [
                    ToolCall(
                        name=tool_call.function.name or "",
                        args=tool_call.function.arguments,
                        id=tool_call.id or "",
                        index=tool_call.index,
                    )
                    for tool_call in tool_calls
                ]
                if tool_calls
                else None
            ),
        )
    elif role == "user":
        return UserMessage(content=content)
    elif role == "system":
        return SystemMessage(content=content)
    elif role is None:
        raise ValueError("Message role cannot be None")
    else:
        raise ValueError(f"Unknown message role {role}")
