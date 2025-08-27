"""update indices and add indexing stage to file

Revision ID: 9c1be04ff4a9
Revises: f6196e2ceaa4
Create Date: 2025-08-26 13:25:13.700959

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from codegraph.graph.models import IndexingStep

# revision identifiers, used by Alembic.
revision: str = "9c1be04ff4a9"
down_revision: Union[str, Sequence[str], None] = "f6196e2ceaa4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # drop unnecessary indices
    op.drop_index("ix_source_node", table_name="node__references")
    op.drop_index("ix_files_project", table_name="files")
    op.drop_constraint("uq_aliases_local_global_project", "aliases", type_="unique")

    # add indexing step column
    op.add_column(
        "files",
        sa.Column("indexing_step", sa.String, nullable=False, server_default=IndexingStep.COMPLETE),
    )
    op.create_index(
        "ix_files_project_indexing_step", "files", ["project_id", "indexing_step"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # drop indexing step column
    op.drop_index("ix_files_project_indexing_step", table_name="files")
    op.drop_column("files", "indexing_step")

    # add back dropped indices
    op.create_unique_constraint(
        "uq_aliases_local_global_project",
        "aliases",
        ["local_qualifier", "global_qualifier", "project_id"],
    )
    op.create_index("ix_files_project", "files", ["project_id"], unique=False)
    op.create_index("ix_source_node", "node__references", ["source_node_id"], unique=False)
