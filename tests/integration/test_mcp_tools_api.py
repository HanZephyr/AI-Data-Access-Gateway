from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from adg.app.main import create_app
from adg.audit.models import AuditEvent
from adg.control_plane.db import create_engine_from_url, create_session_factory, get_session
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.directory import Role, User, UserRole
from adg.control_plane.models.governance import ResourcePolicy
from adg.control_plane.models.resource import Resource
from adg.shared.security import hash_api_key


def build_mcp_app() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            User(
                id="user_1",
                name="Alice",
                external_ref="u001",
                org_node_id=None,
                status="active",
            )
        )
        session.add(Role(id="role_finance", name="Finance"))
        session.add(UserRole(user_id="user_1", role_id="role_finance"))
        session.add(
            ApiKey(
                id="key_runtime",
                name="runtime",
                key_hash=hash_api_key("adg_runtime"),
                user_id="user_1",
                status="active",
                scopes='["runtime"]',
            )
        )
        session.add(
            ApiKey(
                id="key_admin_only",
                name="admin-only",
                key_hash=hash_api_key("adg_admin_only"),
                status="active",
                scopes='["admin"]',
            )
        )
        session.add(
            ApiKey(
                id="key_runtime_unbound",
                name="runtime-unbound",
                key_hash=hash_api_key("adg_runtime_unbound"),
                status="active",
                scopes='["runtime"]',
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
            Resource(
                id="res_customers",
                datasource_id="ds_1",
                parent_id=None,
                kind="relational_table",
                name="customers",
                path="warehouse.public.customers",
                display_name="customers",
                query_language="sql",
                status="active",
                metadata_json="{}",
            )
        )
        session.add(
            ResourcePolicy(
                subject_type="user",
                subject_id="user_1",
                effect="allow",
                action="read",
                resource_id="res_customers",
                status="active",
            )
        )
        session.commit()

    app = create_app()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), session_factory


def test_mcp_tool_route_accepts_non_admin_api_key() -> None:
    client, _ = build_mcp_app()

    response = client.post(
        "/api/tools/list_datasources",
        json={},
        headers={"X-ADG-API-Key": "adg_runtime"},
    )

    assert response.status_code == 200
    assert response.json()["datasources"][0]["id"] == "ds_1"


def test_mcp_tool_route_rejects_unknown_tool_name() -> None:
    client, _ = build_mcp_app()

    response = client.post(
        "/api/tools/not_a_tool",
        json={},
        headers={"X-ADG-API-Key": "adg_runtime"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown MCP tool"


def test_mcp_tool_route_rejects_request_identity_fields() -> None:
    client, _ = build_mcp_app()

    response = client.post(
        "/api/tools/list_datasources",
        json={"user_id": "spoofed", "roles": ["admin"], "groups": ["finance"]},
        headers={"X-ADG-API-Key": "adg_runtime"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Runtime identity fields are not accepted"


def test_mcp_tool_route_commits_runtime_audit_events() -> None:
    client, session_factory = build_mcp_app()

    response = client.post(
        "/api/tools/list_datasources",
        json={},
        headers={"X-ADG-API-Key": "adg_runtime"},
    )

    assert response.status_code == 200
    with session_factory() as session:
        event = session.execute(select(AuditEvent)).scalar_one()
    assert event.event_type == "metadata_discovery"
    assert event.user_id == "user_1"


def test_mcp_tool_route_rejects_api_key_without_runtime_scope() -> None:
    client, _ = build_mcp_app()

    response = client.post(
        "/api/tools/list_datasources",
        json={},
        headers={"X-ADG-API-Key": "adg_admin_only"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Runtime scope required"


def test_mcp_tool_route_rejects_runtime_key_without_user_binding() -> None:
    client, _ = build_mcp_app()

    response = client.post(
        "/api/tools/list_datasources",
        json={},
        headers={"X-ADG-API-Key": "adg_runtime_unbound"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Runtime key must be bound to a user"
