from time import monotonic, sleep
from typing import Any, cast

from chromadb import Collection, HttpClient
from chromadb.api import ClientAPI
from chromadb.api.types import Embeddable, EmbeddingFunction
from sentence_transformers import SentenceTransformer

from codegraph.configs.app_configs import (
    CHROMA_DB,
    CHROMA_HOST,
    CHROMA_PORT,
    CHROMA_TENANT,
    READINESS_INTERVAL,
    READINESS_TIMEOUT,
)
from codegraph.configs.indexing import EMBEDDING_MODEL
from codegraph.utils.logging import get_logger

logger = get_logger()


class ChromaIndex:
    _embedding_model: SentenceTransformer | None = None

    @classmethod
    def init_index(cls) -> None:
        if cls._embedding_model:
            return

        try:
            cls._embedding_model = SentenceTransformer(
                EMBEDDING_MODEL, trust_remote_code=True, local_files_only=True
            )
        except OSError:
            cls._embedding_model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)
        cls._create_collection()

    @classmethod
    def _create_collection(cls) -> None:
        client = _get_chroma_client()
        client.get_or_create_collection(
            name=_get_collection_name(),
            configuration={
                "hnsw": {"space": "l2"},  # normalized so same as cosine
            },
        )

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
    def get_query_collection(cls) -> Collection:
        client = _get_chroma_client()
        collection: Collection = client.get_collection(
            name=_get_collection_name(),
            embedding_function=cast(
                EmbeddingFunction[Embeddable],
                lambda x: cls.get_embedding_model().encode_query(x, normalize_embeddings=True),
            ),
        )
        return collection

    @classmethod
    def get_index_collection(cls) -> Collection:
        client = _get_chroma_client()
        collection: Collection = client.get_collection(
            name=_get_collection_name(),
            embedding_function=cast(
                EmbeddingFunction[Embeddable],
                lambda x: cls.get_embedding_model().encode_document(x, normalize_embeddings=True),
            ),
        )
        return collection

    @classmethod
    def wipe_collection(cls) -> None:
        client = _get_chroma_client()
        client.delete_collection(name=_get_collection_name())
        cls._create_collection()


def _get_chroma_client() -> ClientAPI:
    return HttpClient(host=CHROMA_HOST, port=CHROMA_PORT, tenant=CHROMA_TENANT, database=CHROMA_DB)


def _get_collection_name() -> str:
    return f"codegraph-{EMBEDDING_MODEL.replace('/', '-')}"


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
