"""add root path to project

Revision ID: ca6730e75f09
Revises: 64fe4bda3973
Create Date: 2025-08-24 20:20:50.456022

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ca6730e75f09"
down_revision: Union[str, Sequence[str], None] = "64fe4bda3973"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "projects", sa.Column("root_path", sa.String(), nullable=False, server_default="")
    )
    # backfill root path
    op.execute(
        """
        UPDATE projects
        SET root_path = (
            SELECT path
            FROM files
            WHERE files.id = projects.root_file_id
        )
        WHERE root_file_id IS NOT NULL
        """
    )
    op.create_unique_constraint("uq_projects_root_path", "projects", ["root_path"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_projects_root_path", "projects", type_="unique")
    op.drop_column("projects", "root_path")
