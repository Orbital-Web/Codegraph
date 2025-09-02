import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from codegraph.graph.models import IndexingStep, Language, NodeType


class Base(DeclarativeBase):
    pass


# ------------------------- ASSOCIATION TABLES ------------------------- #


class Node__Reference(Base):
    __tablename__ = "node__references"

    source_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    target_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    line_number: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        PrimaryKeyConstraint("source_node_id", "target_node_id", "line_number"),
        # source_node_id is covered by primary key
        Index("ix_target_node", "target_node_id"),
    )


# ------------------------- TABLES ------------------------- #


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    root_path: Mapped[str] = mapped_column(String)
    languages: Mapped[list[Language]] = mapped_column(ARRAY(String), default=[])
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    root_file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("files.id"))

    # relationships
    root_file: Mapped["File | None"] = relationship(foreign_keys=[root_file_id], uselist=False)
    files: Mapped[list["File"]] = relationship(
        back_populates="project",
        foreign_keys="File.project_id",
        cascade="all, delete-orphan",
        single_parent=True,
        passive_deletes=True,
    )
    nodes: Mapped[list["Node"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        single_parent=True,
        passive_deletes=True,
    )
    aliases: Mapped[list["Alias"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        single_parent=True,
        passive_deletes=True,
    )

    __table_args__ = (UniqueConstraint("root_path", name="uq_projects_root_path"),)


class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    language: Mapped[Language | None] = mapped_column(String)
    indexing_step: Mapped[IndexingStep] = mapped_column(String)
    chunks: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))

    # relationships
    parent: Mapped["File | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["File"]] = relationship(
        back_populates="parent", passive_deletes=True, single_parent=True
    )
    project: Mapped["Project"] = relationship(back_populates="files", foreign_keys=[project_id])
    nodes: Mapped[list["Node"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
        single_parent=True,
        passive_deletes=True,
    )
    aliases: Mapped[list["Alias"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
        single_parent=True,
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_files_parent", "parent_id"),
        # project_id is covered by ix_files_project_last_indexed_at
        Index("ix_files_project_last_indexed_at", "project_id", "last_indexed_at"),
        Index("ix_files_project_indexing_step", "project_id", "indexing_step"),
        UniqueConstraint("path", "project_id", name="uq_files_path_project"),
    )


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    global_qualifier: Mapped[str] = mapped_column(String)  # e.g foo.bar.baz, unique within project
    definition: Mapped[str | None] = mapped_column(Text)
    type: Mapped[NodeType] = mapped_column(String)

    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))

    # relationships
    file: Mapped["File"] = relationship(back_populates="nodes")
    project: Mapped["Project"] = relationship(back_populates="nodes")

    __table_args__ = (
        Index("ix_nodes_name_project", "name", "project_id"),
        # name, file_id covered by ix_nodes_name_project (no need for composite, match is small)
        Index("ix_nodes_type_project", "type", "project_id"),  # TODO: unused
        Index("ix_nodes_file", "file_id"),
        UniqueConstraint(
            "global_qualifier", "project_id", name="uq_nodes_global_qualifier_project"
        ),
    )


class Alias(Base):
    __tablename__ = "aliases"

    local_qualifier: Mapped[str] = mapped_column(String)  # unique within project
    global_qualifier: Mapped[str] = mapped_column(String)  # many local to one global allowed

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"))

    # relationships
    project: Mapped["Project"] = relationship(back_populates="aliases")
    file: Mapped["File"] = relationship(back_populates="aliases")

    __table_args__ = (
        PrimaryKeyConstraint("local_qualifier", "project_id"),
        Index("ix_alias_file", "file_id"),
    )
