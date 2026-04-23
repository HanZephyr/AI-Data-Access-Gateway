from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from adg.app.dependencies import AuthenticatedApiKey, require_api_key
from adg.control_plane.db import create_engine_from_url, create_session_factory, get_session
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.shared.security import hash_api_key


def build_test_app(raw_key: str) -> FastAPI:
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
                scopes='["mcp","internal","admin"]',
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
