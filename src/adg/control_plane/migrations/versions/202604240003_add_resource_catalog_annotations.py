"""Add editable resource catalog annotations and disable flags."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "202604240003"
down_revision: str | None = "202604240002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add fields that preserve operator-maintained catalog metadata."""

    inspector = inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    if "resources" in existing_tables:
        resource_columns = {column["name"] for column in inspector.get_columns("resources")}
        with op.batch_alter_table("resources") as batch_op:
            if "description" not in resource_columns:
                batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
            if "status" not in resource_columns:
                batch_op.add_column(
                    sa.Column(
                        "status",
                        sa.String(length=32),
                        nullable=False,
                        server_default="active",
                    )
                )
        if not _has_index(inspector, "resources", "ix_resources_status"):
            op.create_index("ix_resources_status", "resources", ["status"])

    if "resource_fields" in existing_tables:
        field_columns = {column["name"] for column in inspector.get_columns("resource_fields")}
        with op.batch_alter_table("resource_fields") as batch_op:
            if "status" not in field_columns:
                batch_op.add_column(
                    sa.Column(
                        "status",
                        sa.String(length=32),
                        nullable=False,
                        server_default="active",
                    )
                )
        if not _has_index(inspector, "resource_fields", "ix_resource_fields_status"):
            op.create_index("ix_resource_fields_status", "resource_fields", ["status"])


def downgrade() -> None:
    """Remove catalog annotation columns added for the resource-tree console."""

    inspector = inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    if "resource_fields" in existing_tables:
        if _has_index(inspector, "resource_fields", "ix_resource_fields_status"):
            op.drop_index("ix_resource_fields_status", table_name="resource_fields")
        field_columns = {column["name"] for column in inspector.get_columns("resource_fields")}
        if "status" in field_columns:
            with op.batch_alter_table("resource_fields") as batch_op:
                batch_op.drop_column("status")

    if "resources" in existing_tables:
        if _has_index(inspector, "resources", "ix_resources_status"):
            op.drop_index("ix_resources_status", table_name="resources")
        resource_columns = {column["name"] for column in inspector.get_columns("resources")}
        with op.batch_alter_table("resources") as batch_op:
            if "status" in resource_columns:
                batch_op.drop_column("status")
            if "description" in resource_columns:
                batch_op.drop_column("description")


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    """Return whether an index already exists on a table in the current database."""

    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))
