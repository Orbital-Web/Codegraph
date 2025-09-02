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
    token_count: int
    file_id: UUID
    node_ids: list[UUID]
    language: Language | None


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
