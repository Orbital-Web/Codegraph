from pydantic import BaseModel

from codegraph.agent.llm.models import ToolResponse


class ToolCallFormat(BaseModel):
    name: str
    args: str


class IterationToolResponse(BaseModel):
    iteration: int
    response: ToolResponse
