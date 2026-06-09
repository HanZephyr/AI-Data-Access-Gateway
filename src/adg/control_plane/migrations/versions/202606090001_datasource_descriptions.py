"""datasource descriptions

Revision ID: 202606090001
Revises: 202604260002
Create Date: 2026-06-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606090001"
down_revision: str | None = "202604260002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store operator-authored datasource descriptions for runtime discovery."""

    with op.batch_alter_table("datasources") as batch_op:
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove datasource descriptions on rollback."""

    with op.batch_alter_table("datasources") as batch_op:
        batch_op.drop_column("description")
