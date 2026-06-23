from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, cast

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

from adg.app import auth_rate_limit
from adg.app.dependencies import (
    AuthenticatedApiKey,
    authenticate_api_key_value,
    require_api_key,
)
from adg.app.settings import get_settings
from adg.control_plane.db import create_engine_from_url, create_session_factory, get_session
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.shared.security import hash_api_key


def configure_auth_rate_limit(
    monkeypatch: MonkeyPatch,
    *,
    enabled: bool = True,
    storage: str = "memory",
    redis_url: str | None = None,
    max_failures: int = 2,
) -> None:
    monkeypatch.setenv("ADG_AUTH_RATE_LIMIT_ENABLED", str(enabled).lower())
    monkeypatch.setenv("ADG_AUTH_RATE_LIMIT_STORAGE", storage)
    monkeypatch.setenv("ADG_AUTH_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("ADG_AUTH_RATE_LIMIT_MAX_FAILURES", str(max_failures))
    monkeypatch.setenv("ADG_AUTH_RATE_LIMIT_BLOCK_SECONDS", "300")
    if redis_url is None:
        monkeypatch.delenv("ADG_AUTH_RATE_LIMIT_REDIS_URL", raising=False)
    else:
        monkeypatch.setenv("ADG_AUTH_RATE_LIMIT_REDIS_URL", redis_url)
    get_settings.cache_clear()
    auth_rate_limit.reset_auth_rate_limiter()


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


def test_require_api_key_matches_by_direct_hash_lookup() -> None:
    class FakeScalarResult:
        def __init__(self, value: object | None) -> None:
            self._value = value

        def scalar_one_or_none(self) -> object | None:
            return self._value

    class FakeSession:
        def __init__(self, api_key: ApiKey) -> None:
            self.api_key = api_key
            self.captured_statement: object | None = None

        def execute(self, statement: object) -> FakeScalarResult:
            self.captured_statement = statement
            return FakeScalarResult(self.api_key)

    raw_key = "adg_direct_lookup"
    api_key = ApiKey(
        id="key_lookup",
        name="lookup",
        key_hash=hash_api_key(raw_key),
        status="active",
        scopes='["admin"]',
    )
    session = FakeSession(api_key)

    authenticated = authenticate_api_key_value(cast(Session, session), raw_key)

    assert authenticated.id == "key_lookup"
    compiled = str(session.captured_statement)
    assert "api_keys.key_hash" in compiled
    assert "api_keys.status" in compiled


def test_require_api_key_rate_limits_repeated_failures(monkeypatch: MonkeyPatch) -> None:
    configure_auth_rate_limit(monkeypatch, max_failures=2)
    try:
        client = TestClient(build_test_app("adg_valid"))

        first = client.get("/protected", headers={"X-ADG-API-Key": "adg_wrong"})
        second = client.get("/protected", headers={"X-ADG-API-Key": "adg_wrong"})

        assert first.status_code == 401
        assert second.status_code == 429
        assert second.json()["detail"] == "Too many authentication failures"
    finally:
        get_settings.cache_clear()
        auth_rate_limit.reset_auth_rate_limiter()


def test_require_api_key_rate_limits_key_spraying_from_same_client(
    monkeypatch: MonkeyPatch,
) -> None:
    configure_auth_rate_limit(monkeypatch, max_failures=2)
    try:
        client = TestClient(build_test_app("adg_valid"))

        first = client.get("/protected", headers={"X-ADG-API-Key": "adg_wrong_1"})
        second = client.get("/protected", headers={"X-ADG-API-Key": "adg_wrong_2"})

        assert first.status_code == 401
        assert second.status_code == 429
        assert second.json()["detail"] == "Too many authentication failures"
    finally:
        get_settings.cache_clear()
        auth_rate_limit.reset_auth_rate_limiter()
def test_require_api_key_success_does_not_clear_client_spraying_bucket(
    monkeypatch: MonkeyPatch,
) -> None:
    configure_auth_rate_limit(monkeypatch, max_failures=2)
    try:
        client = TestClient(build_test_app("adg_valid"))

        first_failure = client.get(
            "/protected",
            headers={"X-ADG-API-Key": "adg_wrong_1"},
        )
        success = client.get("/protected", headers={"X-ADG-API-Key": "adg_valid"})
        second_failure = client.get(
            "/protected",
            headers={"X-ADG-API-Key": "adg_wrong_2"},
        )

        assert first_failure.status_code == 401
        assert success.status_code == 200
        assert second_failure.status_code == 429
        assert second_failure.json()["detail"] == "Too many authentication failures"
    finally:
        get_settings.cache_clear()
        auth_rate_limit.reset_auth_rate_limiter()
def test_require_api_key_success_clears_failure_count(monkeypatch: MonkeyPatch) -> None:
    configure_auth_rate_limit(monkeypatch, max_failures=2)
    try:
        client = TestClient(build_test_app("adg_valid"))
        auth_rate_limit.record_auth_failure("adg_valid")

        success = client.get("/protected", headers={"X-ADG-API-Key": "adg_valid"})
        after_success = client.get("/protected", headers={"X-ADG-API-Key": "adg_valid_typo"})

        assert success.status_code == 200
        assert after_success.status_code == 401
        assert auth_rate_limit.check_auth_rate_limited("adg_valid") is False
    finally:
        get_settings.cache_clear()
        auth_rate_limit.reset_auth_rate_limiter()


def test_require_api_key_rate_limit_can_be_disabled(monkeypatch: MonkeyPatch) -> None:
    configure_auth_rate_limit(monkeypatch, enabled=False, max_failures=1)
    try:
        client = TestClient(build_test_app("adg_valid"))

        first = client.get("/protected", headers={"X-ADG-API-Key": "adg_wrong"})
        second = client.get("/protected", headers={"X-ADG-API-Key": "adg_wrong"})

        assert first.status_code == 401
        assert second.status_code == 401
    finally:
        get_settings.cache_clear()
        auth_rate_limit.reset_auth_rate_limiter()


def test_require_api_key_redis_rate_limits_key_spraying_from_same_client(
    monkeypatch: MonkeyPatch,
) -> None:
    class FakeRedisClient:
        def __init__(self) -> None:
            self.values: dict[str, int] = {}
            self.expirations: dict[str, int] = {}

        def incr(self, key: str) -> int:
            self.values[key] = self.values.get(key, 0) + 1
            return self.values[key]

        def expire(self, key: str, seconds: int) -> None:
            self.expirations[key] = seconds

        def setex(self, key: str, seconds: int, value: int) -> None:
            self.values[key] = value
            self.expirations[key] = seconds

        def exists(self, key: str) -> int:
            return int(key in self.values)

        def delete(self, *keys: str) -> None:
            for key in keys:
                self.values.pop(key, None)
                self.expirations.pop(key, None)

    fake_redis = FakeRedisClient()
    monkeypatch.setattr(auth_rate_limit, "create_redis_client", lambda _: fake_redis)
    configure_auth_rate_limit(
        monkeypatch,
        storage="redis",
        redis_url="redis://localhost:6379/0",
        max_failures=2,
    )
    try:
        client = TestClient(build_test_app("adg_valid"))

        first = client.get("/protected", headers={"X-ADG-API-Key": "adg_wrong_1"})
        second = client.get("/protected", headers={"X-ADG-API-Key": "adg_wrong_2"})

        assert first.status_code == 401
        assert second.status_code == 429
        assert second.json()["detail"] == "Too many authentication failures"
    finally:
        get_settings.cache_clear()
        auth_rate_limit.reset_auth_rate_limiter()
def test_require_api_key_rate_limit_supports_redis_backend(
    monkeypatch: MonkeyPatch,
) -> None:
    class FakeRedisClient:
        def __init__(self) -> None:
            self.values: dict[str, int] = {}
            self.expirations: dict[str, int] = {}

        def incr(self, key: str) -> int:
            self.values[key] = self.values.get(key, 0) + 1
            return self.values[key]

        def expire(self, key: str, seconds: int) -> None:
            self.expirations[key] = seconds

        def setex(self, key: str, seconds: int, value: int) -> None:
            self.values[key] = value
            self.expirations[key] = seconds

        def exists(self, key: str) -> int:
            return int(key in self.values)

        def delete(self, *keys: str) -> None:
            for key in keys:
                self.values.pop(key, None)
                self.expirations.pop(key, None)

    fake_redis = FakeRedisClient()
    monkeypatch.setattr(auth_rate_limit, "create_redis_client", lambda _: fake_redis)
    configure_auth_rate_limit(
        monkeypatch,
        storage="redis",
        redis_url="redis://localhost:6379/0",
        max_failures=2,
    )
    try:
        client = TestClient(build_test_app("adg_valid"))

        first = client.get("/protected", headers={"X-ADG-API-Key": "adg_wrong"})
        second = client.get("/protected", headers={"X-ADG-API-Key": "adg_wrong"})

        assert first.status_code == 401
        assert second.status_code == 429
        assert fake_redis.expirations
    finally:
        get_settings.cache_clear()
        auth_rate_limit.reset_auth_rate_limiter()
