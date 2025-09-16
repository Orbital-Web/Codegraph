from pydantic import BaseModel


class ToolCallFormat(BaseModel):
    name: str
    args: str
