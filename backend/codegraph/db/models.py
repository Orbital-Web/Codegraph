from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

from codegraph.graph.models import NodeType, ReferenceType


class Base(DeclarativeBase):
    pass


# ------------------------- ASSOCIATION TABLES ------------------------- #


class Node__Reference(Base):
    __tablename__ = "node__references"

    source_node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True
    )
    target_node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True
    )
    relationship_type: Mapped[ReferenceType] = mapped_column(Enum(ReferenceType))


# ------------------------- TABLES ------------------------- #


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    root_file_id: Mapped[int] = mapped_column(ForeignKey("files.id"))

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    path: Mapped[Path] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE")
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )

    # relationships
    parent: Mapped["File" | None] = relationship(
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

    __table_args__ = (Index("ix_files_path", "path"),)


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    implementation: Mapped[str] = mapped_column(Text)
    type: Mapped[NodeType] = mapped_column(Enum(NodeType))

    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"))

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
    )
