from typing import Any, cast
from uuid import UUID

from chromadb.api.types import Metadata

from codegraph.graph.models import Chunk, InferenceChunk, Language


def get_doc_id(file_id: UUID, chunk_id: int) -> str:
    """Returns the corresponding index `doc_id` for a given `file_id` and `chunk_id`."""
    return f"{file_id}:{chunk_id}"


def get_chunk_doc_id(chunk: Chunk | InferenceChunk) -> str:
    """Returns the corresponding index `doc_id` for a given `chunk`."""
    return get_doc_id(chunk.file_id, chunk.chunk_id)


def split_doc_id(doc_id: str) -> tuple[UUID, int]:
    """Returns the corresponding chunk `file_id` and `chunk_id` for a given index `doc_id`."""
    file_id, chunk_id = doc_id.split(":", 1)
    return UUID(file_id), int(chunk_id)


def get_chunk_doc_metadata(chunk: Chunk) -> Metadata:
    """Returns the corresponding index `doc_metadata` for a given `chunk`."""
    return {
        "token_count": chunk.token_count,
        "node_ids": ",".join(str(node_id) for node_id in chunk.node_ids),
        "language": chunk.language.value if chunk.language else "",
    }


def split_doc_metadata(doc_metadata: Metadata) -> dict[str, Any]:
    """Returns the corresponding chunk `metadata` for a given index `doc_metadata`."""
    return {
        "token_count": cast(int, doc_metadata["token_count"]),
        "node_ids": (
            [UUID(node_id) for node_id in cast(str, doc_metadata["node_ids"]).split(",")]
            if doc_metadata["node_ids"]
            else []
        ),
        "language": Language(doc_metadata["language"]) if doc_metadata["language"] else None,
    }


def doc_to_chunk(doc_id: str, doc_text: str, doc_metadata: Metadata) -> Chunk:
    """Converts an index document to a chunk."""
    file_id, chunk_id = split_doc_id(doc_id)
    metadata = split_doc_metadata(doc_metadata)

    return Chunk(text=doc_text, file_id=file_id, chunk_id=chunk_id, **metadata)


def doc_to_inference_chunk(
    doc_id: str, doc_text: str, doc_metadata: Metadata, doc_distance: float
) -> InferenceChunk:
    """Converts an index document to an inference chunk."""
    file_id, chunk_id = split_doc_id(doc_id)
    metadata = split_doc_metadata(doc_metadata)

    return InferenceChunk(
        text=doc_text, file_id=file_id, chunk_id=chunk_id, score=doc_distance, **metadata
    )
