import pytest
from pytest import MonkeyPatch

from adg.app.settings import Settings


def test_settings_defaults_are_local_friendly() -> None:
    settings = Settings()

    assert settings.env == "local"
    assert settings.service_name == "AI Data Access Gateway"
    assert settings.api_key_header == "X-ADG-API-Key"
    assert settings.control_plane_database_url.startswith("sqlite:///")


def test_settings_read_adg_prefixed_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ADG_ENV", "test")
    monkeypatch.setenv("ADG_CONTROL_PLANE_DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("ADG_SECRET_KEY", "unit-test-secret")

    settings = Settings()

    assert settings.env == "test"
    assert settings.control_plane_database_url == "sqlite:///./test.db"
    assert settings.secret_key == "unit-test-secret"


def test_settings_reject_default_secret_key_in_production(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ADG_ENV", "production")
    monkeypatch.delenv("ADG_SECRET_KEY", raising=False)

    with pytest.raises(ValueError, match="ADG_SECRET_KEY"):
        Settings()
