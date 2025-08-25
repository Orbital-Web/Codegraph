"""add last indexed to file

Revision ID: f6196e2ceaa4
Revises: ca6730e75f09
Create Date: 2025-08-24 21:20:22.947016

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6196e2ceaa4"
down_revision: Union[str, Sequence[str], None] = "ca6730e75f09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "files",
        sa.Column(
            "last_indexed_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_files_project_last_indexed_at",
        "files",
        ["project_id", "last_indexed_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_files_project_last_indexed_at", "files")
    op.drop_column("files", "last_indexed_at")
