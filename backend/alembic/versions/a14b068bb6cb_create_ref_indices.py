"""create ref indices

Revision ID: a14b068bb6cb
Revises: c3a09e199c08
Create Date: 2025-08-22 20:36:41.882719

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a14b068bb6cb"
down_revision: Union[str, Sequence[str], None] = "c3a09e199c08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_source_node", "node__references", ["source_node_id"], unique=False)
    op.create_index("ix_target_node", "node__references", ["target_node_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_target_node", table_name="node__references")
    op.drop_index("ix_source_node", table_name="node__references")
