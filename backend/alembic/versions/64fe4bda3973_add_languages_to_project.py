"""add languages to project

Revision ID: 64fe4bda3973
Revises: a14b068bb6cb
Create Date: 2025-08-23 21:13:04.992271

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "64fe4bda3973"
down_revision: Union[str, Sequence[str], None] = "a14b068bb6cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "projects",
        sa.Column("languages", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("projects", "languages")
