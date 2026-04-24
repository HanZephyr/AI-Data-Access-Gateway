from datetime import UTC, datetime, timedelta
from uuid import UUID

from adg.audit.models import AuditEvent
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.governance import FieldPolicy, ResourcePolicy, ResourceTag, Tag
from adg.control_plane.models.masking import DecryptContext, MaskingPolicy
from adg.control_plane.models.resource import Resource, ResourceField


def assert_uuidv7(value: str) -> None:
    parsed = UUID(value)
    assert str(parsed) == value
    assert parsed.version == 7


def test_control_plane_primary_keys_default_to_uuidv7(db_session) -> None:
    datasource = Datasource(
        tenant_id="tenant-a",
        name="Warehouse",
        type="postgres",
        datasource_kind="relational",
        config_json="{}",
        status="active",
    )
    db_session.add(datasource)
    db_session.flush()

    resource = Resource(
        tenant_id="tenant-a",
        datasource_id=datasource.id,
        kind="relational_table",
        name="customers",
        path="warehouse.public.customers",
        display_name="Customers",
        query_language="sql",
        metadata_json="{}",
    )
    db_session.add(resource)
    db_session.flush()

    field = ResourceField(
        tenant_id="tenant-a",
        datasource_id=datasource.id,
        resource_id=resource.id,
        name="email",
        data_type="varchar",
        nullable=True,
        ordinal_position=1,
        metadata_json="{}",
    )
    tag = Tag(tenant_id="tenant-a", name="pii", category="classification")
    db_session.add_all([field, tag])
    db_session.flush()

    records = [
        datasource,
        resource,
        field,
        tag,
        ResourceTag(tenant_id="tenant-a", tag_id=tag.id, resource_id=resource.id),
        ResourcePolicy(
            tenant_id="tenant-a",
            subject_type="role",
            subject_id="analyst",
            effect="allow",
            action="read",
            resource_id=resource.id,
        ),
        FieldPolicy(
            tenant_id="tenant-a",
            subject_type="all",
            subject_id="*",
            effect="deny",
            resource_id=resource.id,
            field_name="email",
            action="read",
        ),
        MaskingPolicy(
            tenant_id="tenant-a",
            resource_id=resource.id,
            field_name="email",
            strategy="partial",
            config_json='{"prefix":2,"suffix":3}',
        ),
        DecryptContext(
            tenant_id="tenant-a",
            query_id="query-1",
            user_id="user-1",
            datasource_id=datasource.id,
            key_ciphertext="ciphertext",
            allowed_fields_json="[]",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        ),
        ApiKey(name="admin", key_hash="hash", status="active", scopes='["admin"]'),
        AuditEvent(
            tenant_id="tenant-a",
            user_id="user-1",
            api_key_id=None,
            event_type="metadata_discovery",
            datasource_id=datasource.id,
            resource_ids_json="[]",
            query_id=None,
            sql_text=None,
            decision="allowed",
            reason=None,
            metadata_json="{}",
        ),
    ]
    db_session.add_all(records)
    db_session.flush()

    for record in records:
        assert_uuidv7(record.id)
