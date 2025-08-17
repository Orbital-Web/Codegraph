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
        sa.Column("root_file_id", sa.UUID(), nullable=True),
        # defer fk creation
        # sa.ForeignKeyConstraint(["root_file_id"], ["files.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "files",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_files_project", "files", ["project_id"], unique=False)
    op.create_index("ix_files_parent", "files", ["parent_id"], unique=False)
    op.create_unique_constraint("uq_files_path_project", "files", ["path", "project_id"])

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
        sa.Column("global_qualifier", sa.String(), nullable=False),
        sa.Column("definition", sa.Text(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("file_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nodes_name_project", "nodes", ["name", "project_id"], unique=False)
    op.create_index("ix_nodes_type_project", "nodes", ["type", "project_id"], unique=False)
    op.create_index("ix_nodes_file", "nodes", ["file_id"], unique=False)
    op.create_unique_constraint(
        "uq_nodes_global_qualifier_project", "nodes", ["global_qualifier", "project_id"]
    )

    op.create_table(
        "aliases",
        sa.Column("local_qualifier", sa.String(), nullable=False),
        sa.Column("global_qualifier", sa.String(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("local_qualifier", "project_id"),
    )
    op.create_unique_constraint(
        "uq_aliases_local_global_project",
        "aliases",
        ["local_qualifier", "global_qualifier", "project_id"],
    )

    op.create_table(
        "node__references",
        sa.Column("source_node_id", sa.UUID(), nullable=False),
        sa.Column("target_node_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("source_node_id", "target_node_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("node__references")

    op.drop_constraint("uq_aliases_local_global_project", "aliases", type_="unique")
    op.drop_table("aliases")

    op.drop_constraint("uq_nodes_global_qualifier_project", "nodes", type_="unique")
    op.drop_index("ix_nodes_file", table_name="nodes")
    op.drop_index("ix_nodes_type_project", table_name="nodes")
    op.drop_index("ix_nodes_name_project", table_name="nodes")
    op.drop_table("nodes")

    op.drop_constraint("fk_projects_root_file", "projects", type_="foreignkey")

    op.drop_constraint("uq_files_path_project", "files", type_="unique")
    op.drop_index("ix_files_parent", table_name="files")
    op.drop_index("ix_files_project", table_name="files")
    op.drop_table("files")

    op.drop_table("projects")
