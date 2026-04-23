from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

from adg.app.dependencies import AuthenticatedApiKey, require_api_key
from adg.app.settings import get_settings
from adg.control_plane.db import create_engine_from_url, create_session_factory, get_session
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.shared.security import hash_api_key


def build_test_app(
    raw_key: str,
    *,
    scopes: str = '["mcp","internal","admin"]',
    expires_at: datetime | None = None,
) -> FastAPI:
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            ApiKey(
                id="key_123",
                name="test",
                key_hash=hash_api_key(raw_key),
                status="active",
                scopes=scopes,
                expires_at=expires_at,
            )
        )
        session.commit()

    app = FastAPI()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    @app.get("/protected")
    def protected(
        api_key: Annotated[AuthenticatedApiKey, Depends(require_api_key)],
    ) -> dict[str, str]:
        return {"api_key_id": api_key.id}

    return app


def test_require_api_key_accepts_valid_key() -> None:
    client = TestClient(build_test_app("adg_valid"))

    response = client.get("/protected", headers={"X-ADG-API-Key": "adg_valid"})

    assert response.status_code == 200
    assert response.json() == {"api_key_id": "key_123"}


def test_require_api_key_rejects_missing_key() -> None:
    client = TestClient(build_test_app("adg_valid"))

    response = client.get("/protected")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"


def test_require_api_key_rejects_wrong_key() -> None:
    client = TestClient(build_test_app("adg_valid"))

    response = client.get("/protected", headers={"X-ADG-API-Key": "adg_wrong"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"


def test_require_api_key_rejects_expired_key() -> None:
    client = TestClient(
        build_test_app(
            "adg_expired",
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
    )

    response = client.get("/protected", headers={"X-ADG-API-Key": "adg_expired"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Expired API key"


def test_require_api_key_honors_configured_header(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ADG_API_KEY_HEADER", "X-Custom-ADG-Key")
    get_settings.cache_clear()
    try:
        client = TestClient(build_test_app("adg_custom"))

        response = client.get("/protected", headers={"X-Custom-ADG-Key": "adg_custom"})

        assert response.status_code == 200
        assert response.json() == {"api_key_id": "key_123"}
    finally:
        monkeypatch.delenv("ADG_API_KEY_HEADER", raising=False)
        get_settings.cache_clear()
