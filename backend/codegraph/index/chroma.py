from time import monotonic, sleep
from typing import Any, cast
from uuid import UUID

from chromadb import Collection, EmbeddingFunction, HttpClient
from chromadb.api import ClientAPI
from chromadb.api.types import Embeddable, Embeddings, Where, WhereDocument
from sqlalchemy.orm import Session

from codegraph.configs.app_configs import (
    CHROMA_DB,
    CHROMA_HOST,
    CHROMA_PORT,
    CHROMA_TENANT,
    READINESS_INTERVAL,
    READINESS_TIMEOUT,
)
from codegraph.configs.indexing import EMBEDDING_MODEL, EMBEDDING_SPACE, NUM_RETRIEVED_CHUNKS
from codegraph.db.models import File
from codegraph.graph.models import Chunk, InferenceChunk
from codegraph.index.chunk_utils import (
    doc_to_chunk,
    doc_to_inference_chunk,
    get_chunk_doc_id,
    get_chunk_doc_metadata,
    get_doc_id,
)
from codegraph.model_service.client import embed_texts
from codegraph.utils.logging import get_logger

logger = get_logger()


class ChromaIndexManager:
    """A class that manages the ChromaIndex and embedding model."""

    class Embedder(EmbeddingFunction[Embeddable]):
        def __init__(self) -> None:
            pass

        def __call__(self, input: Embeddable) -> Embeddings:
            return cast(
                Embeddings,
                embed_texts(cast(list[str], input), normalize=EMBEDDING_SPACE == "cosine"),
            )

        @staticmethod
        def name() -> str:
            return EMBEDDING_MODEL

        @staticmethod
        def build_from_config(config: dict[str, Any]) -> "ChromaIndexManager.Embedder":
            return ChromaIndexManager.Embedder()

        def get_config(self) -> dict[str, Any]:
            return {}

    @classmethod
    def _get_collection_name(cls, project_id: int) -> str:
        return f"codegraph-{project_id}-{EMBEDDING_MODEL.replace('/', '-')}"

    @classmethod
    def get_or_create_index(cls, project_id: int) -> "ChromaIndex":
        client = _get_chroma_client()
        collection_name = cls._get_collection_name(project_id)

        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=ChromaIndexManager.Embedder(),
            configuration={
                "hnsw": {
                    "space": "l2" if EMBEDDING_SPACE == "l2" else "ip"
                },  # if 'cosine', we normalize the embeddings instead
            },
        )
        return ChromaIndex(project_id, collection)

    @classmethod
    def delete_index(cls, project_id: int) -> None:
        client = _get_chroma_client()
        client.delete_collection(name=cls._get_collection_name(project_id))

    @classmethod
    def delete_all_indices(cls) -> None:
        client = _get_chroma_client()
        for collection in client.list_collections():
            client.delete_collection(name=collection.name)


class ChromaIndex:
    """A thread-safe class for indexing and querying chunks in a collection."""

    def __init__(self, project_id: int, collection: Collection) -> None:
        self.project_id = project_id
        self.collection = collection

    def upsert(self, chunks: list[Chunk]) -> None:
        """Adds a list of chunks to the index. If the chunk already exists, it's embeddings and
        metadata will get updated.
        """
        self.collection.upsert(
            ids=[get_chunk_doc_id(chunk) for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[get_chunk_doc_metadata(chunk) for chunk in chunks],
        )

    def delete(self, file: File) -> None:
        """Deletes chunks associated with the given `file`. Does not modify the `file` database
        object."""
        chunk_ids = [get_doc_id(file.id, chunk_id) for chunk_id in range(file.chunks)]
        if chunk_ids:
            self.collection.delete(ids=chunk_ids)

    def delete_ids(self, file_ids: list[UUID], session: Session) -> None:
        """Deletes chunks associated with the given list of `file_ids`. Does not modify the `File`
        database objects. The `File` objects must still exist for this function to work.
        """
        chunk_ids: list[str] = []
        for row in session.query(File.id, File.chunks).filter(File.id.in_(file_ids)).all():
            chunk_ids.extend(get_doc_id(row.id, chunk_id) for chunk_id in range(row.chunks))
        if chunk_ids:
            self.collection.delete(ids=chunk_ids)

    def query(
        self,
        query_text: str,
        n_results: int = NUM_RETRIEVED_CHUNKS,
        where: Where | None = None,  # TODO: create custom filter class
        where_document: WhereDocument | None = None,
    ) -> list[InferenceChunk]:
        """Queries the index by semantic similarity. Optionally filters based on metadata or
        document content.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"],
        )
        return [
            doc_to_inference_chunk(*doc_data)
            for doc_data in zip(
                results["ids"][0],
                (results["documents"] or [])[0],
                (results["metadatas"] or [])[0],
                (results["distances"] or [])[0],
            )
        ]

    def get(
        self,
        limit: int = 100,
        offset: int = 0,
        where: Where | None = None,  # TODO: create custom filter class
        where_document: WhereDocument | None = None,
    ) -> list[Chunk]:
        """Returns a list of chunks in the index. Optionally filters based on metadata or document
        content.
        """
        results = self.collection.get(
            limit=limit,
            offset=offset,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas"],
        )

        return [
            doc_to_chunk(*doc_data)
            for doc_data in zip(
                results["ids"],
                results["documents"] or [],
                results["metadatas"] or [],
            )
        ]

    def count(self) -> int:
        """Returns the total number of chunks in this index."""
        return self.collection.count()


def _get_chroma_client() -> ClientAPI:
    return HttpClient(host=CHROMA_HOST, port=CHROMA_PORT, tenant=CHROMA_TENANT, database=CHROMA_DB)


def wait_for_index() -> bool:
    logger.info("Index: readiness probe starting")

    start_time = monotonic()
    ready = False

    while True:
        try:
            if _get_chroma_client():
                ready = True
                break
        except Exception:
            pass

        elapsed = monotonic() - start_time
        if elapsed > READINESS_TIMEOUT:
            break

        logger.warning(
            f"Index: readiness probe ongoing, elapsed: {elapsed:.1f}s "
            f"timeout={READINESS_TIMEOUT:.1f}s)"
        )
        sleep(READINESS_INTERVAL)

    if not ready:
        logger.error(f"Index: readiness probe did not succeed in {READINESS_TIMEOUT}")
        return False

    logger.info(f"Index: readiness probe succeeded")
    return True
