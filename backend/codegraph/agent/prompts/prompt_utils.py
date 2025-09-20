import dataclasses
import json
import re

from openai.types.chat import ChatCompletionToolParam
from pydantic import BaseModel

import codegraph.tools.shared_models as native_tool_models
from codegraph.agent.llm.models import ToolResponse
from codegraph.configs.tools import NATIVE_MCP_TOOL_PREFIX


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
    name = tool_response.tool_call.name
    args = json.dumps(tool_response.tool_call.arguments, indent=4)
    success = tool_response.success
    data = tool_response.data

    if not success:
        data_str = str(data)
    else:
        # this whole section is very scuffed
        if name.startswith(NATIVE_MCP_TOOL_PREFIX + "_"):
            data_str = format_native_tool_response(data)
        elif isinstance(data, dict):
            data_str = json.dumps(data, indent=4)
        else:
            data_str = str(data)

    return (
        f"tool: {name}\nsuccess: {tool_response.success}\n"
        f"<args>\n{args}\n</args>\n"
        f"<response>\n{data_str}\n</response>"
    )


def format_native_tool_response(data: BaseModel) -> str:
    model_name = data.__class__.__name__
    native_model = getattr(native_tool_models, model_name)
    data_model = native_model(**dataclasses.asdict(data))
    data_str: str = data_model.pretty_print()
    return data_str
