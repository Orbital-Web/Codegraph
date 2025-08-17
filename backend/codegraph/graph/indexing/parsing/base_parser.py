from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from sqlalchemy.orm import Session

from codegraph.db.models import Alias, File, Node
from codegraph.graph.models import Language, NodeType


class BaseParser(ABC):
    """A base class for all parsers."""

    _LANGUAGE: ClassVar[Language | None] = None

    def __init__(self, project_id: int, project_root: Path):
        self._project_id = project_id
        self._project_root = project_root

    @abstractmethod
    def extract_definitions(self, filepath: Path) -> None:
        """
        Extracts `File` and defined `Node`s from the file and adds them to the database. Also
        extracts `Alias`es for reference resolution in the next step. `filepath` is absolute.
        This function should create its own session and work in parallel with other parsers.
        """

    @abstractmethod
    def extract_references(self, filepath: Path) -> None:
        """
        Extracts `Node__Reference`s from the file and adds them to the database. `filepath` is
        absolute. This function should create its own session and work in parallel with other
        parsers.
        """

    def _find_file(self, filepath: Path, session: Session) -> File | None:
        """
        Finds a `File` object in the database.
        """
        return (
            session.query(File)
            .filter(File.path == filepath, File.project_id == self._project_id)
            .one_or_none()
        )

    def _create_node(
        self,
        name: str,
        global_qualifier: str,
        definition: str | None,
        node_type: NodeType,
        file: File,
        session: Session,
    ) -> Node:
        """
        Creates a `Node` object and adds it to the database. Does not commit the session.
        """
        db_node = Node(
            name=name,
            global_qualifier=global_qualifier,
            definition=definition,
            type=node_type,
            file_id=file.id,
            project_id=self._project_id,
        )
        session.add(db_node)
        session.flush()
        return db_node

    def _create_alias(self, local_qualifier: str, global_qualifier: str, session: Session) -> Alias:
        """
        Creates an `Alias` object and adds it to the database. Does not commit the session.
        """
        db_alias = Alias(
            local_qualifier=local_qualifier,
            global_qualifier=global_qualifier,
            project_id=self._project_id,
        )
        session.add(db_alias)
        session.flush()
        return db_alias

    @staticmethod
    def _resolve_alias(local_qualifier: str, project_id: int, session: Session) -> Node | None:
        """
        Recursively traverses the `Alias` tree to find the `Node` referenced by the
        `local_qualifier`. Returns `None` if the `local_qualifier` is not found.
        """
        while True:
            alias = (
                session.query(Alias)
                .filter(Alias.local_qualifier == local_qualifier, Alias.project_id == project_id)
                .one_or_none()
            )
            if alias is None:
                break
            local_qualifier = alias.global_qualifier

        return (
            session.query(Node)
            .filter(Node.global_qualifier == local_qualifier, Node.project_id == project_id)
            .one_or_none()
        )
