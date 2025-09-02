"""add chunk count to file

Revision ID: 8a9d88102a98
Revises: 19d589328387
Create Date: 2025-09-02 16:12:05.609824

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a9d88102a98"
down_revision: Union[str, Sequence[str], None] = "19d589328387"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("files", sa.Column("chunks", sa.Integer, nullable=False, server_default="0"))
    # no need to query chroma and set the values as we haven't implemented vector indexing yet


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("files", "chunks")
