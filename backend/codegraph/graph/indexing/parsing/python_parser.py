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
            self._walk_extract_definitions(tree, file, file_text, module_name, session)
            session.commit()

    def extract_references(self, filepath: Path) -> None:
        pass

    # ------------------------- EXTRACT DEFINITION HELPERS ------------------------- #

    def _get_module_name(self, filepath: Path) -> str:
        rel = filepath.relative_to(self._project_root).with_suffix("")
        parts = rel.parts
        # drop __init__
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    def _walk_extract_definitions(
        self, tree: ast.AST, file: File, file_text: str, parent_qualifier: str, session: Session
    ) -> None:
        # handle class and function definitions
        if isinstance(tree, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            global_qualifier = f"{parent_qualifier}.{tree.name}"
            definition = ast.get_source_segment(file_text, tree)
            node_type = NodeType.CLASS if isinstance(tree, ast.ClassDef) else NodeType.FUNCTION

            self._create_node(tree.name, global_qualifier, definition, node_type, file, session)

            for child in tree.body:
                self._walk_extract_definitions(child, file, file_text, global_qualifier, session)

        # handle imports
        elif isinstance(tree, (ast.Import, ast.ImportFrom)):
            for alias in tree.names:
                # TODO: handle global_qualifier for relative imports (both Import and ImportFrom)
                if isinstance(tree, ast.Import):
                    # abc.py: import x.y as foo -> (abc.foo = x)
                    local_name = alias.asname or alias.name.split(".", 1)[0]
                    global_qualifier = alias.name
                else:
                    # abc.py: from x.y import z as bar -> (abc.bar = x.y.z)
                    local_name = alias.asname or alias.name
                    global_qualifier = f"{tree.module}.{alias.name}" if tree.module else alias.name

                local_qualifier = f"{parent_qualifier}.{local_name}"
                self._create_alias(local_qualifier, global_qualifier, session)

        else:
            for child_node in ast.iter_child_nodes(tree):
                self._walk_extract_definitions(
                    child_node, file, file_text, parent_qualifier, session
                )
