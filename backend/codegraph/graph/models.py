from enum import Enum


class NodeType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    TYPE = "type"


class ReferenceType(str, Enum):
    CALLS = "calls"  # function -> function
    INHERITS = "inherits"  # class -> class
    INPUTS = "inputs"  # function -> type
    OUTPUTS = "outputs"  # function -> type


class Language(str, Enum):
    PYTHON = "python"
