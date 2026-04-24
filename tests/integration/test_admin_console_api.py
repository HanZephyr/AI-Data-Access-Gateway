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

    assert (
        len(client.get("/admin/resource-policies?tenant_id=tenant-a", headers=auth()).json())
        == 1
    )
    assert len(client.get("/admin/field-policies?tenant_id=tenant-a", headers=auth()).json()) == 1
    assert (
        len(client.get("/admin/masking-policies?tenant_id=tenant-a", headers=auth()).json())
        == 1
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

    revoked = client.post(f"/admin/api-keys/{key_id}/revoke", headers=auth())
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    audit = client.get("/admin/audit-events?tenant_id=tenant-a", headers=auth())
    assert audit.status_code == 200
    assert audit.json()[0]["event_type"] == "metadata_discovery"

    setup = client.get("/admin/mcp/setup", headers=auth())
    assert setup.status_code == 200
    assert "execute_query" in setup.json()["tools"]
