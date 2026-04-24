from pathlib import Path

from alembic import command
from alembic.config import Config
from pytest import MonkeyPatch
from sqlalchemy import create_engine, inspect

from adg.app.settings import get_settings


def test_initial_migration_creates_foundation_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "control-plane.db"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(config, "head")

    engine = create_engine(db_url)
    tables = set(inspect(engine).get_table_names())
    assert {
        "api_keys",
        "audit_events",
        "datasources",
        "field_policies",
        "resources",
        "resource_fields",
        "resource_policies",
        "resource_tags",
        "tags",
        "alembic_version",
    }.issubset(tables)


def test_migration_uses_database_url_from_environment(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    configured_db_path = tmp_path / "configured-control-plane.db"
    configured_db_url = f"sqlite:///{configured_db_path}"
    default_db_path = tmp_path / "data" / "adg-control-plane.db"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ADG_CONTROL_PLANE_DATABASE_URL", configured_db_url)
    default_db_path.parent.mkdir()
    get_settings.cache_clear()

    try:
        config = Config(str(project_root / "alembic.ini"))
        config.set_main_option(
            "script_location",
            str(project_root / "src" / "adg" / "control_plane" / "migrations"),
        )

        command.upgrade(config, "head")
    finally:
        get_settings.cache_clear()

    configured_tables = set(inspect(create_engine(configured_db_url)).get_table_names())
    assert {
        "api_keys",
        "audit_events",
        "datasources",
        "field_policies",
        "resources",
        "resource_fields",
        "resource_policies",
        "resource_tags",
        "tags",
        "alembic_version",
    }.issubset(configured_tables)
    assert not default_db_path.exists()
