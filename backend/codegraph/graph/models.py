from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel


class NodeType(str, Enum):
    MODULE = "module"
    FUNCTION = "function"
    CLASS = "class"


class Language(str, Enum):
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    CSS = "css"
    GO = "go"
    HTML = "html"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    PHP = "php"
    PYTHON = "python"
    R = "r"
    RUBY = "ruby"
    RUST = "rust"
    TYPESCRIPT = "typescript"


class Chunk(BaseModel):
    text: str
    file_id: UUID
    chunk_id: int

    token_count: int
    node_ids: list[UUID]
    language: Language | None

    @property
    def id(self) -> str:
        return f"{self.file_id}:{self.chunk_id}"

    @property
    def metadata(self) -> dict[str, str | int | float | bool | None]:
        return {
            "token_count": self.token_count,
            "node_ids": ",".join(str(node_id) for node_id in self.node_ids),
            "language": self.language.value if self.language else "",
        }


class InferenceChunk(Chunk):
    score: float


class IndexingStep(str, Enum):
    DEFINITIONS = "definitions"
    REFERENCES = "references"
    VECTOR = "vector"
    COMPLETE = "complete"


INDEXING_STEP_ORDER = (IndexingStep.DEFINITIONS, IndexingStep.REFERENCES, IndexingStep.VECTOR)
NEXT_INDEXING_STEPS = {
    IndexingStep.DEFINITIONS: IndexingStep.REFERENCES,
    IndexingStep.REFERENCES: IndexingStep.VECTOR,
    IndexingStep.VECTOR: IndexingStep.COMPLETE,
}


class IndexingStatus(BaseModel):
    start_time: datetime
    duration: timedelta
    codegraph_indexed_paths: list[Path]
    vector_indexed_paths: list[Path]
