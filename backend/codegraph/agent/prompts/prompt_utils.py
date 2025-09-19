import json
import re

from openai.types.chat import ChatCompletionToolParam
from pydantic import BaseModel

from codegraph.agent.llm.models import ToolResponse


class PromptTemplate:
    """
    A class for building prompt templates with placeholders.
    Useful when building templates with json schemas, as {} will not work with f-strings.
    Unlike string.replace, this class will raise an error if the fields are missing.
    """

    DEFAULT_PATTERN = r"---([a-zA-Z0-9_]+)---"

    def __init__(self, template: str, pattern: str = DEFAULT_PATTERN):
        self._pattern_str = pattern
        self._pattern = re.compile(pattern)
        self._template = template
        self._fields: set[str] = set(self._pattern.findall(template))

    def build(self, **kwargs: str) -> str:
        """
        Build the prompt template with the given fields.
        Will raise an error if the fields are missing.
        Will ignore fields that are not in the template.
        """
        missing = self._fields - set(kwargs.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}.")
        return self._replace_fields(kwargs)

    def partial_build(self, **kwargs: str) -> "PromptTemplate":
        """
        Returns another PromptTemplate with the given fields replaced.
        Will ignore fields that are not in the template.
        """
        new_template = self._replace_fields(kwargs)
        return PromptTemplate(new_template, self._pattern_str)

    def _replace_fields(self, field_vals: dict[str, str]) -> str:
        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            return field_vals.get(key, match.group(0))

        return self._pattern.sub(repl, self._template)


def summarize_tools(tools: list[ChatCompletionToolParam]) -> str:
    return "\n".join(
        f"- {tool['function']['name']}: {tool['function']['description']}" for tool in tools
    )


def format_tools(tools: list[ChatCompletionToolParam]) -> str:
    return "\n".join(json.dumps(tool["function"], indent=4) for tool in tools)


def format_tool(tool: ChatCompletionToolParam) -> str:
    return json.dumps(tool["function"]["parameters"], indent=4)


def format_tool_response(tool_response: ToolResponse) -> str:
    data = tool_response.data
    response_dict = {
        "name": tool_response.tool_call.name,
        "args": tool_response.tool_call.arguments,
        "success": tool_response.success,
        "response": (
            data.model_dump()
            if isinstance(data, BaseModel)
            else data if isinstance(data, dict) else str(data)
        ),
    }
    return json.dumps(response_dict, indent=4)
