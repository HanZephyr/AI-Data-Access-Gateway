"""Add datasource tag bindings and unique tag-binding indexes."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "202604240004"
down_revision: str | None = "202604240003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create datasource tag bindings and prevent duplicate bindings per target."""

    inspector = inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    if "datasource_tags" not in existing_tables:
        op.create_table(
            "datasource_tags",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("tag_id", sa.String(length=36), nullable=False),
            sa.Column("datasource_id", sa.String(length=36), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_datasource_tags_tag_id", "datasource_tags", ["tag_id"])
        op.create_index("ix_datasource_tags_datasource_id", "datasource_tags", ["datasource_id"])

    if "resource_tags" in existing_tables and not _has_index(
        inspector,
        "resource_tags",
        "ux_resource_tags_resource_id_tag_id",
    ):
        op.create_index(
            "ux_resource_tags_resource_id_tag_id",
            "resource_tags",
            ["resource_id", "tag_id"],
            unique=True,
        )

    if "datasource_tags" in set(inspector.get_table_names()) and not _has_index(
        inspector,
        "datasource_tags",
        "ux_datasource_tags_datasource_id_tag_id",
    ):
        op.create_index(
            "ux_datasource_tags_datasource_id_tag_id",
            "datasource_tags",
            ["datasource_id", "tag_id"],
            unique=True,
        )


def downgrade() -> None:
    """Drop datasource tag bindings and duplicate-prevention indexes."""

    inspector = inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    if "datasource_tags" in existing_tables:
        if _has_index(inspector, "datasource_tags", "ux_datasource_tags_datasource_id_tag_id"):
            op.drop_index(
                "ux_datasource_tags_datasource_id_tag_id",
                table_name="datasource_tags",
            )
        if _has_index(inspector, "datasource_tags", "ix_datasource_tags_datasource_id"):
            op.drop_index("ix_datasource_tags_datasource_id", table_name="datasource_tags")
        if _has_index(inspector, "datasource_tags", "ix_datasource_tags_tag_id"):
            op.drop_index("ix_datasource_tags_tag_id", table_name="datasource_tags")
        op.drop_table("datasource_tags")

    if "resource_tags" in existing_tables and _has_index(
        inspector,
        "resource_tags",
        "ux_resource_tags_resource_id_tag_id",
    ):
        op.drop_index("ux_resource_tags_resource_id_tag_id", table_name="resource_tags")


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    """Return whether an index already exists on a table in the current database."""

    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))
