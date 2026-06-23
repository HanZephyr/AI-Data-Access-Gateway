from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from adg.admin_api.datasources import router as admin_datasource_router
from adg.connectors.base import MetadataSnapshot, QueryResult
from adg.connectors.errors import ConnectorOperationError
from adg.connectors.registry import get_connector_registry
from adg.control_plane.db import (
    create_engine_from_url,
    create_session_factory,
    get_session,
)
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.shared.security import hash_api_key


def build_admin_datasource_app() -> TestClient:
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
        session.commit()

    app = FastAPI()
    app.include_router(admin_datasource_router)

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


DATASOURCE_DESCRIPTION = "Primary analytical warehouse for finance and operations."


class FailingDatasourceConnector:
    connector_type = "failing"

    def test_connection(self, config: dict[str, object]) -> None:
        raise ConnectorOperationError("Lost connection to MySQL server at 10.0.0.9")

    def scan_metadata(self, config: dict[str, object]) -> MetadataSnapshot:
        raise ConnectorOperationError("OperationalError postgresql+psycopg://10.0.0.9")

    def execute_query(self, config: dict[str, object], sql: str, limit: int) -> QueryResult:
        raise ConnectorOperationError("Lost connection to MySQL server at 10.0.0.9")


def test_admin_datasource_crud_routes() -> None:
    client = build_admin_datasource_app()
    payload = {
        "name": "Warehouse",
        "type": "postgres",
        "description": DATASOURCE_DESCRIPTION,
        "config": {
            "host": "localhost",
            "port": 5432,
            "username": "alice",
            "password": "secret",
        },
    }

    created = client.post(
        "/admin/datasources",
        json=payload,
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert created.status_code == 201
    created_body = created.json()
    assert "tenant_id" not in created_body
    datasource_id = created_body["id"]
    assert created_body["datasource_kind"] == "relational"
    assert created_body["description"] == "Primary analytical warehouse for finance and operations."
    assert "database" not in created_body["config"]
    assert created_body["config"]["password"] == {
        "kind": "secret_placeholder",
        "configured": True,
    }

    listed = client.get("/admin/datasources", headers={"X-ADG-API-Key": "adg_admin"})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [datasource_id]
    assert listed.json()[0]["description"] == DATASOURCE_DESCRIPTION
    assert listed.json()[0]["config"]["password"] == {
        "kind": "secret_placeholder",
        "configured": True,
    }

    fetched = client.get(
        f"/admin/datasources/{datasource_id}",
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Warehouse"
    assert fetched.json()["description"] == DATASOURCE_DESCRIPTION
    assert fetched.json()["tags"] == []
    assert fetched.json()["config"]["password"] == {
        "kind": "secret_placeholder",
        "configured": True,
    }

    updated = client.patch(
        f"/admin/datasources/{datasource_id}",
        json={
            "name": "Warehouse Replica",
            "description": "Replica used by governed AI agents.",
            "status": "disabled",
            "config": {
                "host": "localhost",
                "port": 5432,
                "username": "alice",
                "password": "",
            },
        },
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Warehouse Replica"
    assert updated.json()["description"] == "Replica used by governed AI agents."
    assert updated.json()["status"] == "disabled"
    assert "database" not in updated.json()["config"]
    assert updated.json()["config"]["password"] == {
        "kind": "secret_placeholder",
        "configured": True,
    }
    assert updated.json()["tags"] == []

    fetched_after_update = client.get(
        f"/admin/datasources/{datasource_id}",
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert fetched_after_update.status_code == 200
    assert fetched_after_update.json()["config"]["password"] == {
        "kind": "secret_placeholder",
        "configured": True,
    }

    cleared = client.patch(
        f"/admin/datasources/{datasource_id}",
        json={"description": None},
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert cleared.status_code == 200
    assert cleared.json()["description"] is None

    deleted = client.delete(
        f"/admin/datasources/{datasource_id}",
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert deleted.status_code == 204

    missing = client.get(
        f"/admin/datasources/{datasource_id}",
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Datasource not found"


def test_admin_datasource_routes_require_admin_key() -> None:
    client = build_admin_datasource_app()

    response = client.get("/admin/datasources")

    assert response.status_code == 401


def test_admin_datasource_returns_404_for_unknown_id() -> None:
    client = build_admin_datasource_app()

    response = client.get(
        "/admin/datasources/ds_missing",
        headers={"X-ADG-API-Key": "adg_admin"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Datasource not found"


def test_admin_datasource_live_operations_sanitize_connector_errors() -> None:
    get_connector_registry().register("failing", FailingDatasourceConnector)
    client = build_admin_datasource_app()

    created = client.post(
        "/admin/datasources",
        json={
            "name": "Failing Warehouse",
            "type": "failing",
            "config": {"host": "10.0.0.9", "username": "alice", "password": "secret"},
        },
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    datasource_id = created.json()["id"]

    for action in ["test", "scan"]:
        response = client.post(
            f"/admin/datasources/{datasource_id}/{action}",
            headers={"X-ADG-API-Key": "adg_admin"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Datasource connector operation failed. Check datasource connectivity and server logs."
        )
        assert "Lost connection" not in response.text
        assert "OperationalError" not in response.text
        assert "10.0.0.9" not in response.text