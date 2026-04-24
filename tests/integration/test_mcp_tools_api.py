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
from adg.shared.security import hash_api_key


def build_mcp_app() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            ApiKey(
                id="key_runtime",
                name="runtime",
                key_hash=hash_api_key("adg_runtime"),
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
        "/mcp/tools/list_datasources",
        json={"user_id": "user-1"},
        headers={"X-ADG-API-Key": "adg_runtime"},
    )

    assert response.status_code == 200
    assert response.json()["datasources"][0]["id"] == "ds_1"


def test_mcp_tool_route_rejects_unknown_tool_name() -> None:
    client, _ = build_mcp_app()

    response = client.post(
        "/mcp/tools/not_a_tool",
        json={"user_id": "user-1"},
        headers={"X-ADG-API-Key": "adg_runtime"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown MCP tool"


def test_mcp_tool_route_commits_runtime_audit_events() -> None:
    client, session_factory = build_mcp_app()

    response = client.post(
        "/mcp/tools/list_datasources",
        json={"user_id": "user-1"},
        headers={"X-ADG-API-Key": "adg_runtime"},
    )

    assert response.status_code == 200
    with session_factory() as session:
        event = session.execute(select(AuditEvent)).scalar_one()
    assert event.event_type == "metadata_discovery"
