from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from adg.app.main import create_app
from adg.control_plane.db import create_engine_from_url, create_session_factory, get_session
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.shared.security import hash_api_key


def test_admin_system_endpoint_requires_api_key() -> None:
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
    client = TestClient(app)

    missing = client.get("/admin/system")
    assert missing.status_code == 401

    ok = client.get("/admin/system", headers={"X-ADG-API-Key": "adg_admin"})
    assert ok.status_code == 200
    assert ok.json() == {
        "service": "AI Data Access Gateway",
        "api_key_id": "key_admin",
    }


def test_admin_system_endpoint_rejects_non_admin_scope_key() -> None:
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            ApiKey(
                id="key_reader",
                name="reader",
                key_hash=hash_api_key("adg_reader"),
                status="active",
                scopes='["mcp"]',
            )
        )
        session.commit()

    app = create_app()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)

    response = client.get("/admin/system", headers={"X-ADG-API-Key": "adg_reader"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin scope required"
