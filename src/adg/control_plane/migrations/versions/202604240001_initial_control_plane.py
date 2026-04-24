"""initial control plane

Revision ID: 202604240001
Revises:
Create Date: 2026-04-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202604240001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the complete tenant-free V1 control-plane schema."""

    op.create_table(
        "datasources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("datasource_kind", sa.String(length=64), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_datasources_type", "datasources", ["type"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=200), nullable=True),
        sa.Column("api_key_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("datasource_id", sa.String(length=36), nullable=True),
        sa.Column("resource_ids_json", sa.Text(), nullable=False),
        sa.Column("query_id", sa.String(length=36), nullable=True),
        sa.Column("sql_text", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])
    op.create_index("ix_audit_events_api_key_id", "audit_events", ["api_key_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_datasource_id", "audit_events", ["datasource_id"])
    op.create_index("ix_audit_events_query_id", "audit_events", ["query_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    op.create_table(
        "resources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("datasource_id", sa.String(length=36), nullable=False),
        sa.Column("parent_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("query_language", sa.String(length=32), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resources_datasource_id", "resources", ["datasource_id"])
    op.create_index("ix_resources_parent_id", "resources", ["parent_id"])
    op.create_index("ix_resources_kind", "resources", ["kind"])
    op.create_index("ix_resources_path", "resources", ["path"])
    op.create_index("ix_resources_scanned_at", "resources", ["scanned_at"])

    op.create_table(
        "resource_fields",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("datasource_id", sa.String(length=36), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("data_type", sa.String(length=200), nullable=False),
        sa.Column("nullable", sa.Boolean(), nullable=False),
        sa.Column("ordinal_position", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resource_fields_datasource_id", "resource_fields", ["datasource_id"])
    op.create_index("ix_resource_fields_resource_id", "resource_fields", ["resource_id"])

    op.create_table(
        "tags",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tags_name", "tags", ["name"])

    op.create_table(
        "resource_tags",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tag_id", sa.String(length=36), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resource_tags_tag_id", "resource_tags", ["tag_id"])
    op.create_index("ix_resource_tags_resource_id", "resource_tags", ["resource_id"])

    op.create_table(
        "resource_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=200), nullable=False),
        sa.Column("effect", sa.String(length=16), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=True),
        sa.Column("tag_id", sa.String(length=36), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resource_policies_subject_type", "resource_policies", ["subject_type"])
    op.create_index("ix_resource_policies_subject_id", "resource_policies", ["subject_id"])
    op.create_index("ix_resource_policies_action", "resource_policies", ["action"])
    op.create_index("ix_resource_policies_resource_id", "resource_policies", ["resource_id"])
    op.create_index("ix_resource_policies_tag_id", "resource_policies", ["tag_id"])
    op.create_index("ix_resource_policies_status", "resource_policies", ["status"])

    op.create_table(
        "field_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=200), nullable=False),
        sa.Column("effect", sa.String(length=16), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("field_name", sa.String(length=200), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_field_policies_subject_type", "field_policies", ["subject_type"])
    op.create_index("ix_field_policies_subject_id", "field_policies", ["subject_id"])
    op.create_index("ix_field_policies_resource_id", "field_policies", ["resource_id"])
    op.create_index("ix_field_policies_field_name", "field_policies", ["field_name"])
    op.create_index("ix_field_policies_action", "field_policies", ["action"])
    op.create_index("ix_field_policies_status", "field_policies", ["status"])

    op.create_table(
        "masking_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("field_name", sa.String(length=200), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=True),
        sa.Column("subject_id", sa.String(length=200), nullable=True),
        sa.Column("strategy", sa.String(length=32), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_masking_policies_resource_id", "masking_policies", ["resource_id"])
    op.create_index("ix_masking_policies_field_name", "masking_policies", ["field_name"])
    op.create_index("ix_masking_policies_subject_type", "masking_policies", ["subject_type"])
    op.create_index("ix_masking_policies_subject_id", "masking_policies", ["subject_id"])
    op.create_index("ix_masking_policies_strategy", "masking_policies", ["strategy"])
    op.create_index("ix_masking_policies_status", "masking_policies", ["status"])

    op.create_table(
        "decrypt_contexts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("query_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=200), nullable=True),
        sa.Column("datasource_id", sa.String(length=36), nullable=False),
        sa.Column("key_ciphertext", sa.Text(), nullable=False),
        sa.Column("allowed_fields_json", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decrypt_contexts_query_id", "decrypt_contexts", ["query_id"])
    op.create_index("ix_decrypt_contexts_user_id", "decrypt_contexts", ["user_id"])
    op.create_index("ix_decrypt_contexts_datasource_id", "decrypt_contexts", ["datasource_id"])
    op.create_index("ix_decrypt_contexts_expires_at", "decrypt_contexts", ["expires_at"])


def downgrade() -> None:
    """Drop V1 control-plane tables in reverse dependency order."""

    op.drop_index("ix_decrypt_contexts_expires_at", table_name="decrypt_contexts")
    op.drop_index("ix_decrypt_contexts_datasource_id", table_name="decrypt_contexts")
    op.drop_index("ix_decrypt_contexts_user_id", table_name="decrypt_contexts")
    op.drop_index("ix_decrypt_contexts_query_id", table_name="decrypt_contexts")
    op.drop_table("decrypt_contexts")
    op.drop_index("ix_masking_policies_status", table_name="masking_policies")
    op.drop_index("ix_masking_policies_strategy", table_name="masking_policies")
    op.drop_index("ix_masking_policies_subject_id", table_name="masking_policies")
    op.drop_index("ix_masking_policies_subject_type", table_name="masking_policies")
    op.drop_index("ix_masking_policies_field_name", table_name="masking_policies")
    op.drop_index("ix_masking_policies_resource_id", table_name="masking_policies")
    op.drop_table("masking_policies")
    op.drop_index("ix_field_policies_status", table_name="field_policies")
    op.drop_index("ix_field_policies_action", table_name="field_policies")
    op.drop_index("ix_field_policies_field_name", table_name="field_policies")
    op.drop_index("ix_field_policies_resource_id", table_name="field_policies")
    op.drop_index("ix_field_policies_subject_id", table_name="field_policies")
    op.drop_index("ix_field_policies_subject_type", table_name="field_policies")
    op.drop_table("field_policies")
    op.drop_index("ix_resource_policies_status", table_name="resource_policies")
    op.drop_index("ix_resource_policies_tag_id", table_name="resource_policies")
    op.drop_index("ix_resource_policies_resource_id", table_name="resource_policies")
    op.drop_index("ix_resource_policies_action", table_name="resource_policies")
    op.drop_index("ix_resource_policies_subject_id", table_name="resource_policies")
    op.drop_index("ix_resource_policies_subject_type", table_name="resource_policies")
    op.drop_table("resource_policies")
    op.drop_index("ix_resource_tags_resource_id", table_name="resource_tags")
    op.drop_index("ix_resource_tags_tag_id", table_name="resource_tags")
    op.drop_table("resource_tags")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_resource_fields_resource_id", table_name="resource_fields")
    op.drop_index("ix_resource_fields_datasource_id", table_name="resource_fields")
    op.drop_table("resource_fields")
    op.drop_index("ix_resources_scanned_at", table_name="resources")
    op.drop_index("ix_resources_path", table_name="resources")
    op.drop_index("ix_resources_kind", table_name="resources")
    op.drop_index("ix_resources_parent_id", table_name="resources")
    op.drop_index("ix_resources_datasource_id", table_name="resources")
    op.drop_table("resources")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_query_id", table_name="audit_events")
    op.drop_index("ix_audit_events_datasource_id", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_index("ix_audit_events_api_key_id", table_name="audit_events")
    op.drop_index("ix_audit_events_user_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index("ix_datasources_type", table_name="datasources")
    op.drop_table("datasources")
