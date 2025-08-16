from datetime import datetime
from pathlib import Path
import uuid

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

from codegraph.graph.models import NodeType, ReferenceType


class Base(DeclarativeBase):
    pass


# ------------------------- ASSOCIATION TABLES ------------------------- #


class Node__Reference(Base):
    __tablename__ = "node__references"

    source_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True
    )
    relationship_type: Mapped[ReferenceType] = mapped_column(String)


# ------------------------- TABLES ------------------------- #


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    root_file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("files.id"))

    # relationships
    root_file: Mapped["File"] = relationship(foreign_keys=[root_file_id])
    files: Mapped[list["File"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        single_parent=True,
        passive_deletes=True,
    )


class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String)
    path: Mapped[Path] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE")
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )

    # relationships
    parent: Mapped["File | None"] = relationship(
        remote_side=[id], back_populates="children"
    )
    children: Mapped[list["File"]] = relationship(
        back_populates="parent", passive_deletes=True, single_parent=True
    )
    project: Mapped["Project"] = relationship(back_populates="files")
    nodes: Mapped[list["Node"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
        single_parent=True,
        passive_deletes=True,
    )

    @property
    def is_folder(self) -> bool:
        return len(self.children) > 0

    __table_args__ = (
        Index("ix_files_path", "path"),
        Index("ix_files_project", "project_id"),
        Index("ix_files_parent", "parent_id"),
    )


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String)
    implementation: Mapped[str] = mapped_column(Text)
    type: Mapped[NodeType] = mapped_column(String)

    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE")
    )

    # relationships
    file: Mapped["File"] = relationship(back_populates="nodes")
    references: Mapped[list["Node"]] = relationship(
        secondary=Node__Reference.__table__,
        primaryjoin=(id == Node__Reference.source_node_id),
        secondaryjoin=(id == Node__Reference.target_node_id),
        back_populates="referenced_by",
    )
    referenced_by: Mapped[list["Node"]] = relationship(
        secondary=Node__Reference.__table__,
        primaryjoin=(id == Node__Reference.target_node_id),
        secondaryjoin=(id == Node__Reference.source_node_id),
        back_populates="references",
    )

    __table_args__ = (
        Index("ix_nodes_name", "name"),
        Index("ix_nodes_type", "type"),
        Index("ix_nodes_file", "file_id"),
    )
