from enum import Enum


class NodeType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"


class Language(str, Enum):
    PYTHON = "python"
