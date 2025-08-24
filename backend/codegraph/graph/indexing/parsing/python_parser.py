import ast
from pathlib import Path

from sqlalchemy.orm import Session

from codegraph.graph.indexing.parsing.base_parser import BaseParser
from codegraph.graph.models import Language, NodeType
from codegraph.utils.logging import get_logger

logger = get_logger()


class PythonParser(BaseParser):
    """A parser for Python files."""

    _LANGUAGE = Language.PYTHON

    def __init__(self, project_id: int, project_root: Path, filepath: Path, session: Session):
        super().__init__(project_id, project_root, filepath, session)

        self._file_text = self._filepath.read_text(encoding="utf-8")

        # get module name
        parts = self._filepath.relative_to(self._project_root).with_suffix("").parts
        if parts[-1] == "__init__":  # drop __init__
            parts = parts[:-1]
        self._module_name = ".".join(parts)

    def extract_definitions(self) -> None:
        # parse file
        try:
            tree = ast.parse(self._file_text, filename=str(self._filepath))
        except SyntaxError:
            logger.warning(f"Syntax error in {self._filepath}, skipping")
            return

        # create module node (could set definition to file_text if we want)
        self._create_node(self._filepath.name, self._module_name, None, NodeType.MODULE)

        # create remaining nodes recursively
        self._walk_extract_definitions(tree, self._module_name)

    def extract_references(self) -> None:
        # parse file
        try:
            tree = ast.parse(self._file_text, filename=str(self._filepath))
        except SyntaxError:
            logger.warning(f"Syntax error in {self._filepath}, skipping")
            return

        # get module node
        module_node = self._find_node(self._module_name)
        assert module_node is not None
        self._module_node = module_node

        # create references
        self._walk_extract_references(tree, self._module_name)

    # ------------------------- EXTRACT DEFINITIONS HELPERS ------------------------- #

    def _create_alias_from_import(self, tree: ast.Import | ast.ImportFrom) -> None:
        for alias in tree.names:
            if isinstance(tree, ast.Import):
                # abc.py: import x.y as foo -> (abc.foo = x.y)
                global_qualifier = alias.name
            else:
                # abc.py: from x.y import z as bar -> (abc.bar = x.y.z)
                parts = [tree.module, alias.name] if tree.module is not None else [alias.name]
                if tree.level > 0:  # handle local imports
                    parts = [*self._module_name.split(".")[: -tree.level], *parts]
                global_qualifier = ".".join(parts)

            local_qualifier = f"{self._module_name}.{alias.asname or alias.name}"
            self._create_alias(local_qualifier, global_qualifier)

    def _walk_extract_definitions(self, tree: ast.AST, scope_qualifier: str) -> None:
        # handle class and function definitions
        if isinstance(tree, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            global_qualifier = f"{scope_qualifier}.{tree.name}"
            definition = ast.get_source_segment(self._file_text, tree)
            node_type = NodeType.CLASS if isinstance(tree, ast.ClassDef) else NodeType.FUNCTION
            self._create_node(tree.name, global_qualifier, definition, node_type)

            # child nodes are scoped under this node
            for child in tree.body:
                self._walk_extract_definitions(child, global_qualifier)

        # handle imports
        elif isinstance(tree, (ast.Import, ast.ImportFrom)):
            self._create_alias_from_import(tree)

        else:
            for child_node in ast.iter_child_nodes(tree):
                self._walk_extract_definitions(child_node, scope_qualifier)

    # ------------------------- EXTRACT REFERENCES HELPERS ------------------------- #

    def _walk_extract_references(self, tree: ast.AST, scope_qualifier: str) -> None:
        # handle class and function definitions
        if isinstance(tree, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            global_qualifier = f"{scope_qualifier}.{tree.name}"
            node = self._find_node(global_qualifier)
            assert node is not None

            # module -> definition
            self._create_reference(self._module_node, node, tree.lineno)
            # parent -> definition
            if scope_qualifier != self._module_name:
                parent_node = self._find_node(scope_qualifier)
                assert parent_node is not None
                self._create_reference(parent_node, node, tree.lineno)

            # child nodes are scoped under this node
            for child in tree.body:
                self._walk_extract_references(child, global_qualifier)

        # TODO: handle other stuff

        else:
            for child_node in ast.iter_child_nodes(tree):
                self._walk_extract_references(child_node, scope_qualifier)
