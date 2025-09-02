from time import monotonic, sleep
from typing import Any, cast
from uuid import UUID

from chromadb import Collection, EmbeddingFunction, HttpClient
from chromadb.api import ClientAPI
from chromadb.api.types import Embeddable, Embeddings, Where, WhereDocument
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from codegraph.configs.app_configs import (
    CHROMA_DB,
    CHROMA_HOST,
    CHROMA_PORT,
    CHROMA_TENANT,
    READINESS_INTERVAL,
    READINESS_TIMEOUT,
)
from codegraph.configs.indexing import EMBEDDING_MODEL, NUM_RETRIEVED_CHUNKS
from codegraph.db.models import File
from codegraph.graph.models import Chunk, InferenceChunk, Language
from codegraph.utils.logging import get_logger

logger = get_logger()


class ChromaIndexManager:
    """A class that manages the ChromaIndex and embedding model."""

    class Embedder(EmbeddingFunction[Embeddable]):
        def __init__(self) -> None:
            self.model = ChromaIndexManager.get_embedding_model()

        def __call__(self, input: Embeddable) -> Embeddings:
            return cast(
                Embeddings,
                self.model.encode_document(cast(list[str], input), normalize_embeddings=True),
            )

        @staticmethod
        def name() -> str:
            return EMBEDDING_MODEL

        @staticmethod
        def build_from_config(config: dict[str, Any]) -> "ChromaIndexManager.Embedder":
            return ChromaIndexManager.Embedder()

        def get_config(self) -> dict[str, Any]:
            return {}

    _embedding_model: SentenceTransformer | None = None

    @classmethod
    def init_manager(cls) -> None:
        if cls._embedding_model:
            return

        try:
            cls._embedding_model = SentenceTransformer(
                EMBEDDING_MODEL, trust_remote_code=True, local_files_only=True
            )
        except OSError:
            cls._embedding_model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)

    @classmethod
    def get_embedding_model(cls) -> SentenceTransformer:
        if not cls._embedding_model:
            raise ValueError("ChromaIndex not initialized. You must call init_index() first.")
        return cls._embedding_model

    @classmethod
    def get_tokenizer(cls) -> Any:
        if not cls._embedding_model:
            raise ValueError("ChromaIndex not initialized. You must call init_index() first.")
        return cls._embedding_model.tokenizer

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
                "hnsw": {"space": "l2"},  # normalized so same as cosine
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
    """A class for indexing and querying chunks in a collection."""

    def __init__(self, project_id: int, collection: Collection) -> None:
        self.project_id = project_id
        self.collection = collection

    def upsert(self, chunks: list[Chunk]) -> None:
        """Adds a list of chunks to the index. If the chunk already exists, it's embeddings and
        metadata will get updated.
        """
        self.collection.upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
        )

    def delete(self, file_ids: list[UUID], session: Session) -> None:
        """Deletes every chunk for the given list of `file_ids`. Requires a db session to find the
        chunks.
        """
        chunk_ids: list[str] = []
        for row in session.query(File.id, File.chunks).filter(File.id.in_(file_ids)).all():
            # TODO: create helper so behavior is consistent
            chunk_ids.extend(f"{row.id}:{chunk_id}" for chunk_id in range(row.chunks))
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
        embedding_model = ChromaIndexManager.get_embedding_model()
        query_embeddings = cast(
            Embeddings, embedding_model.encode_query(query_text, normalize_embeddings=True)
        )
        results = self.collection.query(
            query_embeddings,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"],
        )
        return [
            # TODO: refactor this and models.Chunk, models.InferenceChunk for consistent conversions
            # TODO: maybe a chunk_utils.py inside index
            InferenceChunk(
                text=text,
                file_id=UUID(chunk_id.split(":", 1)[0]),
                chunk_id=int(chunk_id.split(":", 1)[1]),
                token_count=cast(int, metadata["token_count"]),
                node_ids=[UUID(node_id) for node_id in cast(str, metadata["node_ids"]).split(",")],
                language=Language(metadata["language"]) if metadata["language"] else None,
                score=score,
            )
            for chunk_id, text, metadata, score in zip(
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
            Chunk(
                text=text,
                file_id=UUID(chunk_id.split(":", 1)[0]),
                chunk_id=int(chunk_id.split(":", 1)[1]),
                token_count=cast(int, metadata["token_count"]),
                node_ids=[UUID(node_id) for node_id in cast(str, metadata["node_ids"]).split(",")],
                language=Language(metadata["language"]) if metadata["language"] else None,
            )
            for chunk_id, text, metadata in zip(
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
