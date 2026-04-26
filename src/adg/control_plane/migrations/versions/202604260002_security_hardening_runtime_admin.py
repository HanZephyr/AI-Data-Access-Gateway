"""security hardening runtime admin

Revision ID: 202604260002
Revises: 202604260001
Create Date: 2026-04-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202604260002"
down_revision: str | None = "202604260001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop legacy policy priority columns now that deny always wins by rule."""

    with op.batch_alter_table("resource_policies") as batch_op:
        batch_op.drop_column("priority")

    with op.batch_alter_table("field_policies") as batch_op:
        batch_op.drop_column("priority")


def downgrade() -> None:
    """Restore legacy policy priority columns for rollback compatibility."""

    with op.batch_alter_table("resource_policies") as batch_op:
        batch_op.add_column(
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0")
        )

    with op.batch_alter_table("field_policies") as batch_op:
        batch_op.add_column(
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0")
        )
