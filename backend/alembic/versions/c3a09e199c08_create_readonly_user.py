"""create readonly user

Revision ID: c3a09e199c08
Revises: 448151e370ae
Create Date: 2025-08-16 14:01:49.126167

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from codegraph.configs.app_configs import (
    POSTGRES_DB,
    POSTGRES_READONLY_PASSWORD,
    POSTGRES_READONLY_USER,
)

# revision identifiers, used by Alembic.
revision: str = "c3a09e199c08"
down_revision: Union[str, Sequence[str], None] = "448151e370ae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # create user
    op.execute(
        sa.text(
            f"CREATE ROLE {POSTGRES_READONLY_USER} LOGIN PASSWORD '{POSTGRES_READONLY_PASSWORD}'"
        )
    )

    # grant read-only access to currently existing tables
    op.execute(sa.text(f"GRANT CONNECT ON DATABASE {POSTGRES_DB} TO {POSTGRES_READONLY_USER}"))
    op.execute(sa.text(f"GRANT USAGE ON SCHEMA public TO {POSTGRES_READONLY_USER}"))
    op.execute(sa.text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {POSTGRES_READONLY_USER}"))

    # we can use alter default privileges to grant read-only access to future objects
    # but we won't do that for now so we can manually control access to future objects


def downgrade() -> None:
    """Downgrade schema."""
    # revoke privileges
    op.execute(
        sa.text(f"REVOKE SELECT ON ALL SEQUENCES IN SCHEMA public FROM {POSTGRES_READONLY_USER}")
    )
    op.execute(
        sa.text(f"REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM {POSTGRES_READONLY_USER}")
    )
    op.execute(sa.text(f"REVOKE USAGE ON SCHEMA public FROM {POSTGRES_READONLY_USER}"))
    op.execute(sa.text(f"REVOKE CONNECT ON DATABASE {POSTGRES_DB} FROM {POSTGRES_READONLY_USER}"))

    # drop user
    op.execute(sa.text(f"DROP ROLE {POSTGRES_READONLY_USER}"))
