from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func

from codegraph.db.models import Alias, File, Node, Node__Reference
from codegraph.graph.models import Language, NodeType


class BaseParser(ABC):
    """A base class for all parsers. A new parser is created for every file."""

    _LANGUAGE: ClassVar[Language | None] = None

    def __init__(self, project_id: int, project_root: Path, filepath: Path, session: Session):
        """
        Initializes the parser. `filepath` is absolute. `session` is unique to this parser. Either
        `extract_definitions` or `extract_references` will run exactly once per parser. The given
        `session` should not be committed.
        """
        assert filepath.is_file()

        self._project_id = project_id
        self._project_root = project_root
        self._filepath = filepath
        self._session = session
        self._file = (
            session.query(File)
            .filter(File.project_id == self._project_id, File.path == filepath.as_posix())
            .one()
        )

    @abstractmethod
    def extract_definitions(self) -> None:
        """
        Extracts defined `Node`s, definition `Node__Reference`s, and `Alias`es in the file. Its
        internal variables are only visible to this parser.
        """

    @abstractmethod
    def extract_references(self) -> None:
        """
        Extracts `Node__Reference`s between `Node`s defined both in and outside this file. Its
        internal variables are only visible to this parser. Always runs after `extract_definitions`
        runs for all files in the project.
        """

    def _find_node(self, global_qualifier: str) -> Node | None:
        """
        Finds a `Node` object in the database.
        """
        return (
            self._session.query(Node)
            .filter(Node.project_id == self._project_id, Node.global_qualifier == global_qualifier)
            .one_or_none()
        )

    def _create_node(
        self, name: str, global_qualifier: str, definition: str | None, node_type: NodeType
    ) -> Node:
        """
        Creates a `Node` object and adds it to the database. Does not commit the session.
        """
        db_node = Node(
            name=name,
            global_qualifier=global_qualifier,
            definition=definition,
            type=node_type,
            file_id=self._file.id,
            project_id=self._project_id,
        )
        self._session.add(db_node)
        self._session.flush()
        return db_node

    def _create_alias(self, local_qualifier: str, global_qualifier: str) -> Alias:
        """
        Creates an `Alias` object and adds it to the database. Does not commit the session.
        """
        db_alias = Alias(
            local_qualifier=local_qualifier,
            global_qualifier=global_qualifier,
            project_id=self._project_id,
        )
        self._session.add(db_alias)
        self._session.flush()
        return db_alias

    def _create_reference(
        self, source_node: Node, target_node: Node, line_number: int
    ) -> Node__Reference:
        """
        Creates a `Node__Reference` object and adds it to the database. Does not commit the session.
        """
        db_reference = Node__Reference(
            source_node_id=source_node.id, target_node_id=target_node.id, line_number=line_number
        )
        self._session.add(db_reference)
        self._session.flush()
        return db_reference

    def _resolve_alias(self, local_qualifier: str) -> Node | None:
        """
        Recursively traverses the `Alias` tree to find the `Node` referenced by the
        `local_qualifier`. Returns `None` if the `local_qualifier` is not found.
        """
        parts = local_qualifier.split(".")

        # search for partial or full alias match
        prefixes = [".".join(parts[:i]) for i in range(len(parts), 0, -1)]
        alias = (
            self._session.query(Alias)
            .filter(Alias.project_id == self._project_id, Alias.local_qualifier.in_(prefixes))
            .order_by(func.char_length(Alias.local_qualifier).desc())
            .limit(1)
            .one_or_none()
        )

        # replace matched portion of alias
        if alias:
            prefix = alias.global_qualifier
            suffix = local_qualifier[len(alias.local_qualifier) :].lstrip(".")
            new_qualifier = f"{prefix}.{suffix}" if suffix else prefix
            return self._resolve_alias(new_qualifier)

        # no alias match, might be a node
        return self._find_node(local_qualifier)
