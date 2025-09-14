import re
from typing import Type, TypeVar

from pydantic import BaseModel

from codegraph.agent.llm.chat_llm import LLM
from codegraph.agent.llm.models import BaseMessage, ReasoningEffort

SchemaType = TypeVar("SchemaType", bound=BaseModel)

JSON_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def invoke_llm_json(
    llm: LLM,
    messages: list[BaseMessage],
    schema: Type[SchemaType],
    *,
    reasoning_effort: ReasoningEffort | None = None,
    timeout: float | None = None,
    max_tokens: int | None = None,
) -> SchemaType:
    """Invoke an LLM and format the response as an object of the provided `schema`."""
    supports_schema = llm.supports_structured_response()

    content = llm.invoke(
        messages,
        response_schema=schema if supports_schema else None,
        reasoning_effort=reasoning_effort,
        timeout=timeout,
        max_tokens=max_tokens,
    ).content

    if not supports_schema:
        # try our best to extract the json bit
        content = content.replace("\n", " ")
        if json_block_match := JSON_PATTERN.search(content):
            content = json_block_match.group(1)
        else:
            content = content[content.find("{") : content.rfind("}") + 1]

    return schema.model_validate_json(content)


async def ainvoke_llm_json(
    llm: LLM,
    messages: list[BaseMessage],
    schema: Type[SchemaType],
    *,
    reasoning_effort: ReasoningEffort | None = None,
    timeout: float | None = None,
    max_tokens: int | None = None,
) -> SchemaType:
    """Invoke an LLM and format the response as an object of the provided `schema`."""
    supports_schema = llm.supports_structured_response()

    response = await llm.ainvoke(
        messages,
        response_schema=schema if supports_schema else None,
        reasoning_effort=reasoning_effort,
        timeout=timeout,
        max_tokens=max_tokens,
    )
    content = response.content

    if not supports_schema:
        # try our best to extract the json bit
        content = content.replace("\n", " ")
        if json_block_match := JSON_PATTERN.search(content):
            content = json_block_match.group(1)
        else:
            content = content[content.find("{") : content.rfind("}") + 1]

    return schema.model_validate_json(content)
