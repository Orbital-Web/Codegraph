import os

from codegraph.graph.models import Language

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "jinaai/jina-embeddings-v2-base-code")
INDEXING_CHUNK_SIZE = int(os.getenv("INDEXING_CHUNK_SIZE", "512"))
INDEXING_CHUNK_OVERLAP = int(os.getenv("INDEXING_CHUNK_OVERLAP", "0"))

MAX_INDEXING_WORKERS = int(os.getenv("MAX_INDEXING_WORKERS", "40"))
INDEXING_BATCH_SIZE = int(os.getenv("INDEXING_BATCH_SIZE", MAX_INDEXING_WORKERS))

MAX_INDEXING_FILE_SIZE = int(os.getenv("MAX_INDEXING_FILE_SIZE", "10"))  # MB
DIRECTORY_SKIP_INDEXING_PATTERN = os.getenv(
    "DIRECTORY_SKIP_INDEXING_PATTERN", r"^\..*|^__[A-Za-z]*__$|^node_modules$"
)

FILETYPE_LANGUAGES: dict[str, Language] = {
    ".c": Language.C,
    ".h": Language.C,
    ".cpp": Language.CPP,
    ".hpp": Language.CPP,
    ".cs": Language.CSHARP,
    ".css": Language.CSS,
    "scss": Language.CSS,
    "sass": Language.CSS,
    ".go": Language.GO,
    ".html": Language.HTML,
    ".java": Language.JAVA,
    ".js": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".php": Language.PHP,
    ".py": Language.PYTHON,
    ".r": Language.R,
    ".rb": Language.RUBY,
    ".rs": Language.RUST,
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
}

INDEXED_FILETYPES: set[str] = {
    # text documents
    ".txt",
    ".md",
    # code
    *FILETYPE_LANGUAGES.keys(),
    # shell
    ".sh",
    ".zsh",
    ".bash",
    # config
    ".conf",
    ".ini",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".lock",
}
