from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from adg.app.main import create_app
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

    app = create_app()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_admin_datasource_crud_routes() -> None:
    client = build_admin_datasource_app()
    payload = {
        "name": "Warehouse",
        "type": "postgres",
        "config": {"host": "localhost", "port": 5432, "database": "warehouse"},
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

    listed = client.get("/admin/datasources", headers={"X-ADG-API-Key": "adg_admin"})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [datasource_id]

    fetched = client.get(
        f"/admin/datasources/{datasource_id}",
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Warehouse"
    assert fetched.json()["tags"] == []

    tag = client.post(
        "/admin/tags",
        json={"name": "critical", "category": "importance"},
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert tag.status_code == 201
    tag_id = tag.json()["id"]

    bound = client.post(
        "/admin/datasource-tags",
        json={"tag_id": tag_id, "datasource_id": datasource_id},
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert bound.status_code == 201
    assert bound.json()["tag_id"] == tag_id
    assert bound.json()["datasource_id"] == datasource_id

    listed_with_tags = client.get("/admin/datasources", headers={"X-ADG-API-Key": "adg_admin"})
    assert listed_with_tags.status_code == 200
    assert listed_with_tags.json()[0]["tags"] == [
        {
            "id": tag_id,
            "name": "critical",
            "category": "importance",
            "description": None,
        }
    ]

    updated = client.patch(
        f"/admin/datasources/{datasource_id}",
        json={
            "name": "Warehouse Replica",
            "status": "disabled",
            "config": {"host": "localhost", "port": 5432, "database": "replica"},
        },
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Warehouse Replica"
    assert updated.json()["status"] == "disabled"
    assert updated.json()["config"]["database"] == "replica"
    assert updated.json()["tags"] == [
        {
            "id": tag_id,
            "name": "critical",
            "category": "importance",
            "description": None,
        }
    ]

    unbound = client.delete(
        f"/admin/datasource-tags?datasource_id={datasource_id}&tag_id={tag_id}",
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert unbound.status_code == 204

    fetched_after_unbind = client.get(
        f"/admin/datasources/{datasource_id}",
        headers={"X-ADG-API-Key": "adg_admin"},
    )
    assert fetched_after_unbind.status_code == 200
    assert fetched_after_unbind.json()["tags"] == []

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
