"""create codegraph tables

Revision ID: 448151e370ae
Revises:
Create Date: 2025-08-16 13:45:21.461617

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "448151e370ae"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("root_file_id", sa.UUID(), nullable=False),
        # defer fk creation
        # sa.ForeignKeyConstraint(["root_file_id"], ["files.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "files",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_files_parent", "files", ["parent_id"], unique=False)
    op.create_index("ix_files_path", "files", ["path"], unique=False)
    op.create_index("ix_files_project", "files", ["project_id"], unique=False)

    # add fk
    op.create_foreign_key(
        "fk_projects_root_file",
        "projects",
        "files",
        ["root_file_id"],
        ["id"],
    )

    op.create_table(
        "nodes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("implementation", sa.Text(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("file_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nodes_file", "nodes", ["file_id"], unique=False)
    op.create_index("ix_nodes_name", "nodes", ["name"], unique=False)
    op.create_index("ix_nodes_type", "nodes", ["type"], unique=False)

    op.create_table(
        "node__references",
        sa.Column("source_node_id", sa.UUID(), nullable=False),
        sa.Column("target_node_id", sa.UUID(), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("source_node_id", "target_node_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("node__references")

    op.drop_index("ix_nodes_type", table_name="nodes")
    op.drop_index("ix_nodes_name", table_name="nodes")
    op.drop_index("ix_nodes_file", table_name="nodes")
    op.drop_table("nodes")

    op.drop_constraint("fk_projects_root_file", "projects", type_="foreignkey")

    op.drop_index("ix_files_project", table_name="files")
    op.drop_index("ix_files_path", table_name="files")
    op.drop_index("ix_files_parent", table_name="files")
    op.drop_table("files")

    op.drop_table("projects")
