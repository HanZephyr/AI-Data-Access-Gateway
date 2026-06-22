import pytest
from pytest import MonkeyPatch

from adg.app.settings import Settings


def test_settings_defaults_are_local_friendly() -> None:
    settings = Settings()

    assert settings.env == "local"
    assert settings.service_name == "AI Data Access Gateway"
    assert settings.api_key_header == "X-ADG-API-Key"
    assert settings.control_plane_database_url.startswith("sqlite:///")
    assert settings.backend_host_port is None
    assert settings.sql_execution_mode == "read_only"
    assert settings.sql_strict_validation is True
    assert settings.runtime_datasource_pool_cache_size == 32
    assert settings.runtime_datasource_pool_idle_ttl_seconds == 300
    assert settings.runtime_datasource_pool_size == 5
    assert settings.runtime_datasource_pool_max_overflow == 0
    assert settings.runtime_datasource_connect_timeout_seconds == 10
    assert settings.runtime_datasource_read_timeout_seconds == 120
    assert settings.runtime_datasource_write_timeout_seconds == 120


def test_settings_read_adg_prefixed_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ADG_ENV", "test")
    monkeypatch.setenv("ADG_CONTROL_PLANE_DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("ADG_SECRET_KEY", "unit-test-secret")
    monkeypatch.setenv("ADG_CREDENTIAL_ENCRYPTION_KEY", "unit-test-credential-key")
    monkeypatch.setenv("ADG_BACKEND_HOST_PORT", "8001")
    monkeypatch.setenv("ADG_SQL_EXECUTION_MODE", "dml")
    monkeypatch.setenv("ADG_SQL_STRICT_VALIDATION", "false")
    monkeypatch.setenv("ADG_RUNTIME_DATASOURCE_POOL_CACHE_SIZE", "8")
    monkeypatch.setenv("ADG_RUNTIME_DATASOURCE_POOL_IDLE_TTL_SECONDS", "60")
    monkeypatch.setenv("ADG_RUNTIME_DATASOURCE_POOL_SIZE", "3")
    monkeypatch.setenv("ADG_RUNTIME_DATASOURCE_POOL_MAX_OVERFLOW", "2")
    monkeypatch.setenv("ADG_RUNTIME_DATASOURCE_CONNECT_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("ADG_RUNTIME_DATASOURCE_READ_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("ADG_RUNTIME_DATASOURCE_WRITE_TIMEOUT_SECONDS", "46")

    settings = Settings()

    assert settings.env == "test"
    assert settings.control_plane_database_url == "sqlite:///./test.db"
    assert settings.secret_key == "unit-test-secret"
    assert settings.credential_encryption_key == "unit-test-credential-key"
    assert settings.backend_host_port == 8001
    assert settings.sql_execution_mode == "dml"
    assert settings.sql_strict_validation is False
    assert settings.runtime_datasource_pool_cache_size == 8
    assert settings.runtime_datasource_pool_idle_ttl_seconds == 60
    assert settings.runtime_datasource_pool_size == 3
    assert settings.runtime_datasource_pool_max_overflow == 2
    assert settings.runtime_datasource_connect_timeout_seconds == 7
    assert settings.runtime_datasource_read_timeout_seconds == 45
    assert settings.runtime_datasource_write_timeout_seconds == 46


def test_settings_reject_default_secret_key_in_production(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ADG_ENV", "production")
    monkeypatch.delenv("ADG_SECRET_KEY", raising=False)

    with pytest.raises(ValueError, match="ADG_SECRET_KEY"):
        Settings()


def test_settings_require_credential_encryption_key_in_production(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADG_ENV", "production")
    monkeypatch.setenv("ADG_SECRET_KEY", "production-secret-key")
    monkeypatch.delenv("ADG_CREDENTIAL_ENCRYPTION_KEY", raising=False)

    with pytest.raises(ValueError, match="ADG_CREDENTIAL_ENCRYPTION_KEY"):
        Settings()


def test_settings_reject_invalid_runtime_pool_values(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ADG_RUNTIME_DATASOURCE_POOL_CACHE_SIZE", "-1")
    with pytest.raises(ValueError, match="runtime_datasource_pool_cache_size"):
        Settings()

    monkeypatch.delenv("ADG_RUNTIME_DATASOURCE_POOL_CACHE_SIZE")
    monkeypatch.setenv("ADG_RUNTIME_DATASOURCE_POOL_IDLE_TTL_SECONDS", "0")
    with pytest.raises(ValueError, match="runtime_datasource_pool_idle_ttl_seconds"):
        Settings()

    monkeypatch.delenv("ADG_RUNTIME_DATASOURCE_POOL_IDLE_TTL_SECONDS")
    monkeypatch.setenv("ADG_RUNTIME_DATASOURCE_CONNECT_TIMEOUT_SECONDS", "0")
    with pytest.raises(ValueError, match="runtime_datasource_connect_timeout_seconds"):
        Settings()
