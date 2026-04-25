from pytest import MonkeyPatch

from adg.control_plane import bootstrap


def test_resolve_bootstrap_database_url_prefers_settings_when_argument_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bootstrap,
        "get_settings",
        lambda: type("SettingsStub", (), {"control_plane_database_url": "sqlite:///./data/from-settings.db"})(),
    )

    assert bootstrap.resolve_bootstrap_database_url(None) == "sqlite:///./data/from-settings.db"
    assert bootstrap.resolve_bootstrap_database_url("sqlite:///./data/manual.db") == "sqlite:///./data/manual.db"
