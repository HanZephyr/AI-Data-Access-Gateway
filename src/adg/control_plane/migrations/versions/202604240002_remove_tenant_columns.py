"""Remove tenant columns from the self-hosted V1 schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202604240002"
down_revision: str | None = "202604240001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TENANT_TABLES = (
    "datasources",
    "audit_events",
    "resources",
    "resource_fields",
    "tags",
    "resource_tags",
    "resource_policies",
    "field_policies",
    "masking_policies",
    "decrypt_contexts",
)


def upgrade() -> None:
    """Drop legacy tenant columns when upgrading an already-created V1 database."""

    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    for table_name in TENANT_TABLES:
        # Fresh databases already use the tenant-free baseline, so this migration is a no-op.
        if table_name not in existing_tables:
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "tenant_id" not in columns:
            continue
        _drop_tenant_index_if_present(inspector, table_name)
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("tenant_id")


def downgrade() -> None:
    """Recreate legacy tenant columns for downgrade compatibility."""

    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    for table_name in TENANT_TABLES:
        if table_name not in existing_tables:
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "tenant_id" in columns:
            continue
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "tenant_id",
                    sa.String(length=100),
                    nullable=False,
                    server_default="default",
                )
            )
        op.create_index(f"ix_{table_name}_tenant_id", table_name, ["tenant_id"])


def _drop_tenant_index_if_present(
    inspector: sa.Inspector,
    table_name: str,
) -> None:
    """Drop the tenant index only when it exists in the inspected legacy schema."""

    index_name = f"ix_{table_name}_tenant_id"
    if any(index["name"] == index_name for index in inspector.get_indexes(table_name)):
        op.drop_index(index_name, table_name=table_name)
