from enum import Enum


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


class IndexingStep(str, Enum):
    DEFINITIONS = "definitions"
    REFERENCES = "references"
