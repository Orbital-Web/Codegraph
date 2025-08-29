"""add file_id to alias

Revision ID: 19d589328387
Revises: 9c1be04ff4a9
Create Date: 2025-08-28 22:34:09.079115

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "19d589328387"
down_revision: Union[str, Sequence[str], None] = "9c1be04ff4a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # initially, make nullable
    op.add_column("aliases", sa.Column("file_id", sa.UUID(), nullable=True))

    # update existing rows to have a valid file_id
    op.execute(
        """
        UPDATE aliases a
        SET file_id =(
            -- find parent file of node with longest matching global_qualifier prefix
            SELECT n.file_id
            FROM nodes n
            WHERE
                a.project_id = n.project_id
                AND a.local_qualifier LIKE n.global_qualifier || '.%'
            ORDER BY LENGTH(n.global_qualifier) DESC
            LIMIT 1
        )
        """
    )

    # if file_id is still null, it means the file was deleted, so the alias shouldn't exist
    # might happen if indexing -> crash -> file delete -> reindexing
    op.execute("DELETE FROM aliases WHERE file_id IS NULL")

    # make non-nullable
    op.alter_column("aliases", "file_id", nullable=False)

    op.create_foreign_key(
        "fk_aliases_file",
        "aliases",
        "files",
        ["file_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_alias_file", "aliases", ["file_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_alias_file", table_name="aliases")
    op.drop_constraint("fk_aliases_file", "aliases", type_="foreignkey")
    op.drop_column("aliases", "file_id")
