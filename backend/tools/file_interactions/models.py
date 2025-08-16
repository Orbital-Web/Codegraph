from pydantic import BaseModel
from pathlib import Path


class FileReadInput(BaseModel):
    path: Path


class FileReadOutput(BaseModel):
    # TODO:
    pass
