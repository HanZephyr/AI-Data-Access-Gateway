import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from adg.app.main import create_app
from adg.app.settings import get_settings
from adg.audit.service import AuditService
from adg.control_plane.db import create_engine_from_url, create_session_factory, get_session
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.directory import OrgNode, User
from adg.control_plane.models.resource import Resource, ResourceField
from adg.shared.security import hash_api_key


def build_console_app(base_url: str = "http://testserver") -> TestClient:
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
                name="Warehouse",
                type="postgres",
                datasource_kind="relational",
                config_json="{}",
                status="active",
            )
        )
        session.add(
            OrgNode(
                id="org_finance",
                name="Finance",
                path="Company/Finance",
                depth=2,
                status="active",
            )
        )
        session.add(
            User(
                id="user-1",
                name="Alice Analyst",
                external_ref="alice",
                org_node_id="org_finance",
                status="active",
            )
        )
        resource = Resource(
            id="res_customers",
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
                id="field_email",
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
            user_id="user-1",
            api_key_id="key_admin",
            event_type="metadata_discovery",
            decision="allowed",
            datasource_id="ds_1",
            resource_ids=[resource.id],
            query_id=None,
            sql_text="select id from public.customers limit 1",
            reason=None,
            metadata={"tool": "test"},
        )
        session.commit()

    app = create_app()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app, base_url=base_url)


def auth() -> dict[str, str]:
    return {"X-ADG-API-Key": "adg_admin"}


def test_admin_resource_and_tag_management() -> None:
    client = build_console_app()

    resources = client.get("/admin/resources", headers=auth())
    assert resources.status_code == 200
    assert resources.json()[0]["id"] == "res_customers"
    assert "tenant_id" not in resources.json()[0]

    fields = client.get("/admin/resources/res_customers/fields", headers=auth())
    assert fields.status_code == 200
    assert fields.json()[0]["name"] == "email"

    created = client.post(
        "/admin/tags",
        json={"name": "pii", "category": "classification"},
        headers=auth(),
    )
    assert created.status_code == 201
    tag_id = created.json()["id"]

    bound = client.post(
        "/admin/resource-tags",
        json={"tag_id": tag_id, "resource_id": "res_customers"},
        headers=auth(),
    )
    assert bound.status_code == 201
    assert bound.json()["tag_id"] == tag_id
    assert bound.json()["resource_id"] == "res_customers"

    tags = client.get("/admin/tags", headers=auth())
    assert [tag["name"] for tag in tags.json()] == ["pii"]
    assert "tenant_id" not in tags.json()[0]

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
    assert resource.json()["tags"] == [
        {
            "id": tag_id,
            "name": "pii",
            "category": "classification",
            "description": "Email and account identifiers",
        }
    ]

    updated_resource = client.patch(
        "/admin/resources/res_customers",
        json={
            "display_name": "Customer Accounts",
            "description": "Stores registered customer account profiles.",
            "status": "disabled",
        },
        headers=auth(),
    )
    assert updated_resource.status_code == 200
    assert updated_resource.json()["display_name"] == "Customer Accounts"
    assert updated_resource.json()["description"] == "Stores registered customer account profiles."
    assert updated_resource.json()["status"] == "disabled"

    updated_field = client.patch(
        "/admin/resource-fields/field_email",
        json={"description": "Primary customer email used for login.", "status": "disabled"},
        headers=auth(),
    )
    assert updated_field.status_code == 200
    assert updated_field.json()["description"] == "Primary customer email used for login."
    assert updated_field.json()["status"] == "disabled"

    tree = client.get("/admin/resource-tree", headers=auth())
    assert tree.status_code == 200
    table_node = tree.json()[0]
    assert table_node["kind"] == "relational_table"
    assert table_node["status"] == "disabled"
    assert table_node["description"] == "Stores registered customer account profiles."
    assert table_node["tags"] == [
        {
            "id": tag_id,
            "name": "pii",
            "category": "classification",
            "description": "Email and account identifiers",
        }
    ]
    assert table_node["children"][0]["type"] == "field"
    assert tree.json()[0]["children"][0]["status"] == "disabled"

    unbound = client.delete(
        f"/admin/resource-tags?resource_id=res_customers&tag_id={tag_id}",
        headers=auth(),
    )
    assert unbound.status_code == 204

    resource_after_unbind = client.get("/admin/resources/res_customers", headers=auth())
    assert resource_after_unbind.status_code == 200
    assert resource_after_unbind.json()["tags"] == []

    deleted_tag = client.delete(f"/admin/tags/{tag_id}", headers=auth())
    assert deleted_tag.status_code == 204

    deleted_resource = client.delete("/admin/resources/res_customers", headers=auth())
    assert deleted_resource.status_code == 204

    missing_resource = client.get("/admin/resources/res_customers", headers=auth())
    assert missing_resource.status_code == 404


def test_admin_tag_catalog_lists_bound_datasource_and_resources() -> None:
    client = build_console_app()

    created = client.post(
        "/admin/tags",
        json={"name": "gold", "category": "tier"},
        headers=auth(),
    )
    assert created.status_code == 201
    tag_id = created.json()["id"]

    datasource_bound = client.post(
        "/admin/datasource-tags",
        json={"tag_id": tag_id, "datasource_id": "ds_1"},
        headers=auth(),
    )
    assert datasource_bound.status_code == 201

    resource_bound = client.post(
        "/admin/resource-tags",
        json={"tag_id": tag_id, "resource_id": "res_customers"},
        headers=auth(),
    )
    assert resource_bound.status_code == 201

    catalog = client.get(f"/admin/tags/{tag_id}/catalog", headers=auth())
    assert catalog.status_code == 200
    body = catalog.json()
    assert len(body) == 1
    datasource_node = body[0]
    assert datasource_node["key"] == "datasource:ds_1"
    assert datasource_node["type"] == "datasource"
    assert datasource_node["id"] == "ds_1"
    assert datasource_node["tags"] == [
        {
            "id": tag_id,
            "name": "gold",
            "category": "tier",
            "description": None,
        }
    ]
    assert datasource_node["children"] == [
        {
            "key": "resource:res_customers",
            "type": "resource",
            "id": "res_customers",
            "datasource_id": "ds_1",
            "parent_id": None,
            "kind": "relational_table",
            "name": "customers",
            "path": "warehouse.public.customers",
            "display_name": "customers",
            "description": None,
            "query_language": "sql",
            "status": "active",
            "scanned_at": datasource_node["children"][0]["scanned_at"],
            "tags": [
                {
                    "id": tag_id,
                    "name": "gold",
                    "category": "tier",
                    "description": None,
                }
            ],
            "children": [],
        }
    ]


def test_admin_policy_and_masking_policy_management() -> None:
    client = build_console_app()

    resource_policy = client.post(
        "/admin/resource-policies",
        json={
            "subject_type": "role",
            "subject_id": "analyst",
            "effect": "allow",
            "action": "read",
            "resource_id": "res_customers",
            "allow_decrypt": True,
        },
        headers=auth(),
    )
    assert resource_policy.status_code == 201
    assert resource_policy.json()["resource_label"] == "customers / warehouse.public.customers"
    assert resource_policy.json()["allow_decrypt"] is True
    assert "priority" not in resource_policy.json()
    resource_policy_id = resource_policy.json()["id"]

    field_policy = client.post(
        "/admin/field-policies",
        json={
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
    assert field_policy.json()["resource_label"] == "customers / warehouse.public.customers"
    assert "priority" not in field_policy.json()
    field_policy_id = field_policy.json()["id"]

    masking = client.post(
        "/admin/masking-policies",
        json={
            "resource_id": "res_customers",
            "field_name": "email",
            "strategy": "fixed",
            "config": {"replacement": "REDACTED"},
        },
        headers=auth(),
    )
    assert masking.status_code == 201
    assert masking.json()["resource_label"] == "customers / warehouse.public.customers"
    masking_policy_id = masking.json()["id"]

    updated_resource_policy = client.patch(
        f"/admin/resource-policies/{resource_policy_id}",
        json={"status": "disabled", "allow_decrypt": False},
        headers=auth(),
    )
    assert updated_resource_policy.status_code == 200
    assert updated_resource_policy.json()["status"] == "disabled"
    assert updated_resource_policy.json()["allow_decrypt"] is False
    assert "priority" not in updated_resource_policy.json()

    updated_field_policy = client.patch(
        f"/admin/field-policies/{field_policy_id}",
        json={"effect": "allow"},
        headers=auth(),
    )
    assert updated_field_policy.status_code == 200
    assert updated_field_policy.json()["effect"] == "allow"
    assert "priority" not in updated_field_policy.json()

    updated_masking = client.patch(
        f"/admin/masking-policies/{masking_policy_id}",
        json={"strategy": "partial", "config": {"prefix": 2, "suffix": 3, "fill": "*"}},
        headers=auth(),
    )
    assert updated_masking.status_code == 200
    assert updated_masking.json()["strategy"] == "partial"
    assert updated_masking.json()["config"]["prefix"] == 2

    assert (
        len(client.get("/admin/resource-policies", headers=auth()).json())
        == 1
    )
    assert "priority" not in client.get("/admin/resource-policies", headers=auth()).json()[0]
    field_policies = client.get("/admin/field-policies", headers=auth()).json()
    masking_policies = client.get("/admin/masking-policies", headers=auth()).json()
    assert len(field_policies) == 1
    assert len(masking_policies) == 1
    assert "tenant_id" not in field_policies[0]
    assert "tenant_id" not in masking_policies[0]
    assert "priority" not in field_policies[0]

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


def test_admin_policy_and_masking_reject_unknown_resource() -> None:
    client = build_console_app()

    resource_policy = client.post(
        "/admin/resource-policies",
        json={
            "subject_type": "role",
            "subject_id": "analyst",
            "effect": "allow",
            "action": "read",
            "resource_id": "missing-resource",
        },
        headers=auth(),
    )
    assert resource_policy.status_code == 404

    field_policy = client.post(
        "/admin/field-policies",
        json={
            "subject_type": "all",
            "subject_id": "*",
            "effect": "deny",
            "resource_id": "missing-resource",
            "field_name": "email",
            "action": "read",
        },
        headers=auth(),
    )
    assert field_policy.status_code == 404

    masking = client.post(
        "/admin/masking-policies",
        json={
            "resource_id": "missing-resource",
            "field_name": "email",
            "strategy": "fixed",
            "config": {"replacement": "REDACTED"},
        },
        headers=auth(),
    )
    assert masking.status_code == 404


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/admin/resource-policies",
            {
                "subject_type": "group",
                "subject_id": "finance",
                "effect": "allow",
                "action": "read",
                "resource_id": "res_customers",
            },
        ),
        (
            "/admin/field-policies",
            {
                "subject_type": "group",
                "subject_id": "finance",
                "effect": "deny",
                "resource_id": "res_customers",
                "field_name": "email",
                "action": "read",
            },
        ),
        (
            "/admin/masking-policies",
            {
                "resource_id": "res_customers",
                "field_name": "email",
                "strategy": "fixed",
                "config": {"replacement": "REDACTED"},
                "subject_type": "group",
                "subject_id": "finance",
            },
        ),
    ],
)
def test_admin_policy_subjects_reject_group_type(
    path: str,
    payload: dict[str, object],
) -> None:
    client = build_console_app()

    response = client.post(path, json=payload, headers=auth())

    assert response.status_code == 422


def test_admin_api_keys_audit_and_mcp_setup() -> None:
    client = build_console_app()

    created = client.post(
        "/admin/api-keys",
        json={"name": "service-operator", "scopes": ["admin"]},
        headers=auth(),
    )
    assert created.status_code == 201
    assert created.json()["api_key"].startswith("adg_")
    key_id = created.json()["id"]

    updated = client.patch(
        f"/admin/api-keys/{key_id}",
        json={"name": "service-admin", "scopes": ["admin"]},
        headers=auth(),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "service-admin"
    assert updated.json()["scopes"] == ["admin"]

    rejected = client.patch(
        f"/admin/api-keys/{key_id}",
        json={"scopes": ["runtime"]},
        headers=auth(),
    )
    assert rejected.status_code == 400
    assert rejected.json() == {"detail": "Only admin scope is allowed on this page"}

    revoked = client.post(f"/admin/api-keys/{key_id}/revoke", headers=auth())
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    audit = client.get("/admin/audit-events", headers=auth())
    assert audit.status_code == 200
    assert audit.json()[0]["event_type"] == "metadata_discovery"
    assert audit.json()[0]["user_id"] == "user-1"
    assert audit.json()[0]["user_name"] == "Alice Analyst"
    assert audit.json()[0]["user_org_path"] == "Company/Finance"
    assert "tenant_id" not in audit.json()[0]
    assert "sql_text" not in audit.json()[0]

    audit_sql = client.get(f"/admin/audit-events/{audit.json()[0]['id']}/sql", headers=auth())
    assert audit_sql.status_code == 200
    assert audit_sql.json() == {
        "id": audit.json()[0]["id"],
        "sql_text": "select id from public.customers limit 1",
    }

    audit_after_sql_view = client.get("/admin/audit-events", headers=auth())
    assert audit_after_sql_view.status_code == 200
    assert any(
        event["event_type"] == "audit_sql_view"
        and event["api_key_id"] == "key_admin"
        and event["metadata"] == {"target_event_id": audit.json()[0]["id"]}
        and "sql_text" not in event
        for event in audit_after_sql_view.json()
    )

    setup = client.get("/admin/mcp/setup", headers=auth())
    assert setup.status_code == 200
    body = setup.json()
    assert body["server_url"] == "http://testserver/mcp"
    assert body["http_tool_url_template"] == "http://testserver/api/tools/{tool_name}"
    assert body["api_key_header"] == "X-ADG-API-Key"
    assert body["identity_source"] == "api_key"
    assert body["auth_mode"] == "key-derived identity"
    assert body["identity_contract"] == {
        "mode": "derived-from-authenticated-key",
        "caller_supplies_identity": False,
        "payload_scope": "business parameters only",
    }
    assert any(tool["name"] == "execute_query" for tool in body["tools"])
    assert any(tool["description"] for tool in body["tools"])
    serialized = json.dumps(body, sort_keys=True)
    assert "user_id" not in serialized
    assert "\"roles\"" not in serialized
    assert "groups" not in serialized


def test_admin_mcp_setup_uses_backend_host_port_for_public_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADG_BACKEND_HOST_PORT", "8001")
    get_settings.cache_clear()
    try:
        client = build_console_app()

        setup = client.get("/admin/mcp/setup", headers=auth())

        assert setup.status_code == 200
        body = setup.json()
        assert body["server_url"] == "http://testserver:8001/mcp"
        assert body["http_tool_url_template"] == "http://testserver:8001/api/tools/{tool_name}"
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    ("base_url", "backend_host_port"),
    [
        ("http://gateway.example.com", "80"),
        ("https://gateway.example.com", "443"),
    ],
)
def test_admin_mcp_setup_omits_standard_public_ports(
    monkeypatch: pytest.MonkeyPatch,
    base_url: str,
    backend_host_port: str,
) -> None:
    monkeypatch.setenv("ADG_BACKEND_HOST_PORT", backend_host_port)
    get_settings.cache_clear()
    try:
        client = build_console_app(base_url=base_url)

        setup = client.get("/admin/mcp/setup", headers=auth())

        assert setup.status_code == 200
        body = setup.json()
        assert body["server_url"] == f"{base_url}/mcp"
        assert body["http_tool_url_template"] == f"{base_url}/api/tools/{{tool_name}}"
    finally:
        get_settings.cache_clear()
