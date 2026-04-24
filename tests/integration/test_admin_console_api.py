from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from adg.app.main import create_app
from adg.audit.service import AuditService
from adg.control_plane.db import create_engine_from_url, create_session_factory, get_session
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.resource import Resource, ResourceField
from adg.shared.security import hash_api_key


def build_console_app() -> TestClient:
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            ApiKey(
                id="key_admin",
                name="admin",
                key_hash=hash_api_key("adg_admin"),
                status="active",
                scopes='["admin"]',
            )
        )
        session.add(
            Datasource(
                id="ds_1",
                tenant_id="tenant-a",
                name="Warehouse",
                type="postgres",
                datasource_kind="relational",
                config_json="{}",
                status="active",
            )
        )
        resource = Resource(
            id="res_customers",
            tenant_id="tenant-a",
            datasource_id="ds_1",
            kind="relational_table",
            name="customers",
            path="warehouse.public.customers",
            display_name="customers",
            query_language="sql",
            metadata_json="{}",
        )
        session.add(resource)
        session.add(
            ResourceField(
                tenant_id="tenant-a",
                datasource_id="ds_1",
                resource_id=resource.id,
                name="email",
                data_type="varchar",
                nullable=True,
                ordinal_position=1,
                metadata_json="{}",
            )
        )
        AuditService(session).record_event(
            tenant_id="tenant-a",
            user_id="user-1",
            api_key_id="key_admin",
            event_type="metadata_discovery",
            decision="allowed",
            datasource_id="ds_1",
            resource_ids=[resource.id],
            query_id=None,
            sql_text=None,
            reason=None,
            metadata={"tool": "test"},
        )
        session.commit()

    app = create_app()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def auth() -> dict[str, str]:
    return {"X-ADG-API-Key": "adg_admin"}


def test_admin_resource_and_tag_management() -> None:
    client = build_console_app()

    resources = client.get("/admin/resources?tenant_id=tenant-a", headers=auth())
    assert resources.status_code == 200
    assert resources.json()[0]["id"] == "res_customers"

    fields = client.get("/admin/resources/res_customers/fields", headers=auth())
    assert fields.status_code == 200
    assert fields.json()[0]["name"] == "email"

    created = client.post(
        "/admin/tags",
        json={"tenant_id": "tenant-a", "name": "pii", "category": "classification"},
        headers=auth(),
    )
    assert created.status_code == 201
    tag_id = created.json()["id"]

    bound = client.post(
        "/admin/resource-tags",
        json={"tenant_id": "tenant-a", "tag_id": tag_id, "resource_id": "res_customers"},
        headers=auth(),
    )
    assert bound.status_code == 201

    tags = client.get("/admin/tags?tenant_id=tenant-a", headers=auth())
    assert [tag["name"] for tag in tags.json()] == ["pii"]

    fetched_tag = client.get(f"/admin/tags/{tag_id}", headers=auth())
    assert fetched_tag.status_code == 200
    assert fetched_tag.json()["name"] == "pii"

    updated_tag = client.patch(
        f"/admin/tags/{tag_id}",
        json={"description": "Email and account identifiers"},
        headers=auth(),
    )
    assert updated_tag.status_code == 200
    assert updated_tag.json()["description"] == "Email and account identifiers"

    resource = client.get("/admin/resources/res_customers", headers=auth())
    assert resource.status_code == 200
    assert resource.json()["display_name"] == "customers"

    updated_resource = client.patch(
        "/admin/resources/res_customers",
        json={"display_name": "Customer Accounts"},
        headers=auth(),
    )
    assert updated_resource.status_code == 200
    assert updated_resource.json()["display_name"] == "Customer Accounts"

    deleted_tag = client.delete(f"/admin/tags/{tag_id}", headers=auth())
    assert deleted_tag.status_code == 204

    deleted_resource = client.delete("/admin/resources/res_customers", headers=auth())
    assert deleted_resource.status_code == 204

    missing_resource = client.get("/admin/resources/res_customers", headers=auth())
    assert missing_resource.status_code == 404


def test_admin_policy_and_masking_policy_management() -> None:
    client = build_console_app()

    resource_policy = client.post(
        "/admin/resource-policies",
        json={
            "tenant_id": "tenant-a",
            "subject_type": "role",
            "subject_id": "analyst",
            "effect": "allow",
            "action": "read",
            "resource_id": "res_customers",
        },
        headers=auth(),
    )
    assert resource_policy.status_code == 201
    resource_policy_id = resource_policy.json()["id"]

    field_policy = client.post(
        "/admin/field-policies",
        json={
            "tenant_id": "tenant-a",
            "subject_type": "all",
            "subject_id": "*",
            "effect": "deny",
            "resource_id": "res_customers",
            "field_name": "email",
            "action": "read",
        },
        headers=auth(),
    )
    assert field_policy.status_code == 201
    field_policy_id = field_policy.json()["id"]

    masking = client.post(
        "/admin/masking-policies",
        json={
            "tenant_id": "tenant-a",
            "resource_id": "res_customers",
            "field_name": "email",
            "strategy": "fixed",
            "config": {"replacement": "REDACTED"},
        },
        headers=auth(),
    )
    assert masking.status_code == 201
    masking_policy_id = masking.json()["id"]

    updated_resource_policy = client.patch(
        f"/admin/resource-policies/{resource_policy_id}",
        json={"priority": 10, "status": "disabled"},
        headers=auth(),
    )
    assert updated_resource_policy.status_code == 200
    assert updated_resource_policy.json()["priority"] == 10
    assert updated_resource_policy.json()["status"] == "disabled"

    updated_field_policy = client.patch(
        f"/admin/field-policies/{field_policy_id}",
        json={"effect": "allow", "priority": 7},
        headers=auth(),
    )
    assert updated_field_policy.status_code == 200
    assert updated_field_policy.json()["effect"] == "allow"
    assert updated_field_policy.json()["priority"] == 7

    updated_masking = client.patch(
        f"/admin/masking-policies/{masking_policy_id}",
        json={"strategy": "partial", "config": {"prefix": 2, "suffix": 3, "fill": "*"}},
        headers=auth(),
    )
    assert updated_masking.status_code == 200
    assert updated_masking.json()["strategy"] == "partial"
    assert updated_masking.json()["config"]["prefix"] == 2

    assert (
        len(client.get("/admin/resource-policies?tenant_id=tenant-a", headers=auth()).json())
        == 1
    )
    assert len(client.get("/admin/field-policies?tenant_id=tenant-a", headers=auth()).json()) == 1
    assert (
        len(client.get("/admin/masking-policies?tenant_id=tenant-a", headers=auth()).json())
        == 1
    )

    assert (
        client.delete(f"/admin/resource-policies/{resource_policy_id}", headers=auth()).status_code
        == 204
    )
    assert (
        client.delete(f"/admin/field-policies/{field_policy_id}", headers=auth()).status_code
        == 204
    )
    assert (
        client.delete(f"/admin/masking-policies/{masking_policy_id}", headers=auth()).status_code
        == 204
    )


def test_admin_api_keys_audit_and_mcp_setup() -> None:
    client = build_console_app()

    created = client.post(
        "/admin/api-keys",
        json={"name": "runtime", "scopes": ["runtime"]},
        headers=auth(),
    )
    assert created.status_code == 201
    assert created.json()["api_key"].startswith("adg_")
    key_id = created.json()["id"]

    updated = client.patch(
        f"/admin/api-keys/{key_id}",
        json={"name": "runtime readonly", "scopes": ["runtime", "readonly"]},
        headers=auth(),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "runtime readonly"
    assert updated.json()["scopes"] == ["runtime", "readonly"]

    revoked = client.post(f"/admin/api-keys/{key_id}/revoke", headers=auth())
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    audit = client.get("/admin/audit-events?tenant_id=tenant-a", headers=auth())
    assert audit.status_code == 200
    assert audit.json()[0]["event_type"] == "metadata_discovery"

    setup = client.get("/admin/mcp/setup", headers=auth())
    assert setup.status_code == 200
    assert "execute_query" in setup.json()["tools"]
