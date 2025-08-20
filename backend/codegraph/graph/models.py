from enum import Enum


class NodeType(str, Enum):
    MODULE = "module"
    FUNCTION = "function"
    CLASS = "class"


class Language(str, Enum):
    PYTHON = "python"
