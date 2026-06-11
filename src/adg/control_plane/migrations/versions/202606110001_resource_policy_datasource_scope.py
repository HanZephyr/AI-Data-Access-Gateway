"""resource policy datasource scope

Revision ID: 202606110001
Revises: 202606090001
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606110001"
down_revision: str | None = "202606090001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add datasource-scoped resource policies."""

    with op.batch_alter_table("resource_policies") as batch_op:
        batch_op.add_column(sa.Column("datasource_id", sa.String(length=36), nullable=True))
        batch_op.create_index(
            "ix_resource_policies_datasource_id",
            ["datasource_id"],
        )


def downgrade() -> None:
    """Remove datasource-scoped resource policies."""

    with op.batch_alter_table("resource_policies") as batch_op:
        batch_op.drop_index("ix_resource_policies_datasource_id")
        batch_op.drop_column("datasource_id")
