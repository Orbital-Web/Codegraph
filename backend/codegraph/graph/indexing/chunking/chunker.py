import re
from pathlib import Path
from uuid import UUID

from chonkie import CodeChunker, SentenceChunker
from chonkie.chunker.base import BaseChunker
from chonkie.types.base import Chunk as ChonkieChunk
from chonkie.types.code import CodeChunk as ChonkieCodeChunk
from sqlalchemy import select
from sqlalchemy.orm import Session

from codegraph.configs.indexing import INDEXING_CHUNK_OVERLAP, INDEXING_CHUNK_SIZE
from codegraph.db.models import File, Node
from codegraph.graph.models import Chunk
from codegraph.index.chroma import ChromaIndex
from codegraph.utils.logging import get_logger

logger = get_logger()


class Chunker:
    """A class that chunks text/code into smaller pieces for indexing."""

    def __init__(
        self, chunk_size: int = INDEXING_CHUNK_SIZE, chunk_overlap: int = INDEXING_CHUNK_OVERLAP
    ):
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._tokenizer = ChromaIndex.get_tokenizer()

    def chunk(self, file: File, session: Session) -> list[Chunk]:
        filepath = Path(file.path)
        language = file.language
        assert filepath.is_file()

        file_text = filepath.read_text(encoding="utf-8")

        if language is None:
            chunker: BaseChunker = SentenceChunker(
                tokenizer_or_token_counter=self._tokenizer,
                chunk_size=self._chunk_size,
                chunk_overlap=self._chunk_overlap,
            )
        else:
            chunker = CodeChunker(
                tokenizer_or_token_counter=self._tokenizer,
                chunk_size=self._chunk_size,
                language=language,
                include_nodes=True,
            )

        chunks = chunker.chunk(file_text)
        return [self._chonkie_chunk_to_chunk(chunk, file, session) for chunk in chunks]

    def _chonkie_chunk_to_chunk(self, chunk: ChonkieChunk, file: File, session: Session) -> Chunk:
        if isinstance(chunk, ChonkieCodeChunk):
            assert chunk.nodes is not None
            node_names: set[str] = set()
            for node in chunk.nodes:
                # TODO: revisit node structure for languages other than 'python' (should be fine)
                # TODO: do we want to include the module node too?
                if node["type"] == "identifier":
                    node_names.add(node["text"])
                else:
                    node_names.update(re.findall(r"(?:def|class) ([A-Za-z0-9_]+)", node["text"]))
            node_ids = self._find_node_ids(node_names, file, session)
        else:
            node_ids = []

        return Chunk(
            text=chunk.text,
            token_count=chunk.token_count,
            file_id=file.id,
            node_ids=node_ids,
            language=file.language,
        )

    def _find_node_ids(self, names: set[str], parent_file: File, session: Session) -> list[UUID]:
        return list(
            session.execute(
                select(Node.id).filter(Node.name.in_(names), Node.file_id == parent_file.id)
            )
            .scalars()
            .all()
        )
