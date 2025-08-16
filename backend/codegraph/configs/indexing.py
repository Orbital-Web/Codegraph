import os

from codegraph.graph.models import Language

MAX_INDEXING_FILE_SIZE = os.getenv("MAX_INDEXING_FILE_SIZE", 10)  # MB

CODEGRAPH_SUPPORTED_FILETYPES: dict[str, Language] = {
    "py": Language.PYTHON,
}

INDEXED_FILETYPES: set[str] = {
    # text documents
    "txt",
    "md",
    # code
    "py",  # python
    "cpp",  # c/c++
    "c",
    "hpp",
    "h",
    "sh",  # shell
    "zsh",
    "bash",
    "js",  # javascript
    "jsx",
    "ts",  # typescript
    "tsx",
    "rs",  # rust
    "cs",  # c#
    "java",  # java
    "go",  # golang
    "r",  # r
    "html",  # html/css
    "css",
    "scss",
    "sass",
    "php",  # php
    "rb",  # ruby
    # config
    "conf",
    "ini",
    "json",
    "yaml",
    "yml",
    "toml",
    "lock",
}
