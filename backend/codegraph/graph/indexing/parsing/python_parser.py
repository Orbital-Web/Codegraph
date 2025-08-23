import ast
from pathlib import Path

from sqlalchemy.orm import Session

from codegraph.db.engine import get_session
from codegraph.db.models import File
from codegraph.graph.indexing.parsing.base_parser import BaseParser
from codegraph.graph.models import Language, NodeType
from codegraph.utils.logging import get_logger

logger = get_logger()


class PythonParser(BaseParser):
    """A parser for Python files."""

    _LANGUAGE = Language.PYTHON

    def extract_definitions(self, filepath: Path) -> None:
        assert filepath.is_file()

        # parse file
        file_text = filepath.read_text(encoding="utf-8")
        try:
            tree = ast.parse(file_text, filename=str(filepath))
        except SyntaxError:
            logger.warning(f"Syntax error in {filepath}, skipping")
            return

        module_name = self._get_module_name(filepath)

        with get_session() as session:
            file = self._find_file(filepath, session)
            assert file is not None

            # create module node (could set definition to file_text if we want)
            self._create_node(filepath.name, module_name, None, NodeType.MODULE, file, session)

            # create remaining nodes recursively
            self._walk_extract_definitions(tree, module_name, module_name, file, file_text, session)
            session.commit()

    def extract_references(self, filepath: Path) -> None:
        assert filepath.is_file()

        # parse file
        file_text = filepath.read_text(encoding="utf-8")
        try:
            tree = ast.parse(file_text, filename=str(filepath))
        except SyntaxError:
            logger.warning(f"Syntax error in {filepath}, skipping")
            return

        module_name = self._get_module_name(filepath)

        with get_session() as session:
            file = self._find_file(filepath, session)
            assert file is not None

            self._walk_extract_references(tree, module_name, module_name, file, session)
            session.commit()

    # ------------------------- HELPERS ------------------------- #

    def _get_module_name(self, filepath: Path) -> str:
        rel = filepath.relative_to(self._project_root).with_suffix("")
        parts = rel.parts
        # drop __init__
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    def _create_alias_from_import(
        self, tree: ast.Import | ast.ImportFrom, file_qualifier: str, session: Session
    ) -> None:
        for alias in tree.names:
            if isinstance(tree, ast.Import):
                # abc.py: import x.y as foo -> (abc.foo = x.y)
                local_name = alias.asname or alias.name
                global_qualifier = alias.name
            else:
                # abc.py: from x.y import z as bar -> (abc.bar = x.y.z)
                local_name = alias.asname or alias.name
                parts = [tree.module, alias.name] if tree.module is not None else [alias.name]

                # handle local imports
                if tree.level > 0:
                    parts = [*file_qualifier.split(".")[: -tree.level], *parts]
                global_qualifier = ".".join(parts)

            local_qualifier = f"{file_qualifier}.{local_name}"
            self._create_alias(local_qualifier, global_qualifier, session)

    def _walk_extract_definitions(
        self,
        tree: ast.AST,
        scope_qualifier: str,
        file_qualifier: str,
        file: File,
        file_text: str,
        session: Session,
    ) -> None:
        # handle class and function definitions
        if isinstance(tree, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            global_qualifier = f"{scope_qualifier}.{tree.name}"
            definition = ast.get_source_segment(file_text, tree)
            node_type = NodeType.CLASS if isinstance(tree, ast.ClassDef) else NodeType.FUNCTION

            self._create_node(tree.name, global_qualifier, definition, node_type, file, session)

            for child in tree.body:
                self._walk_extract_definitions(
                    child, global_qualifier, file_qualifier, file, file_text, session
                )  # child nodes are scoped under this node

        # handle imports
        elif isinstance(tree, (ast.Import, ast.ImportFrom)):
            self._create_alias_from_import(tree, file_qualifier, session)

        else:
            for child_node in ast.iter_child_nodes(tree):
                self._walk_extract_definitions(
                    child_node, scope_qualifier, file_qualifier, file, file_text, session
                )  # child nodes remain in current scope

    def _walk_extract_references(
        self,
        tree: ast.AST,
        scope_qualifier: str,
        file_qualifier: str,
        file: File,
        session: Session,
    ) -> None:
        pass
