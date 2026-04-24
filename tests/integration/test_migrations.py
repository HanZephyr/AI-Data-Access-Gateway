from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import create_engine, inspect, text

from adg.app.main import create_app
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
        "datasource_tags",
        "field_policies",
        "decrypt_contexts",
        "masking_policies",
        "resources",
        "resource_fields",
        "resource_policies",
        "resource_tags",
        "tags",
        "alembic_version",
    }.issubset(tables)
    inspector = inspect(engine)
    for table_name in tables - {"alembic_version"}:
        column_names = {column["name"] for column in inspector.get_columns(table_name)}
        assert "tenant_id" not in column_names


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
        "datasource_tags",
        "field_policies",
        "decrypt_contexts",
        "masking_policies",
        "resources",
        "resource_fields",
        "resource_policies",
        "resource_tags",
        "tags",
        "alembic_version",
    }.issubset(configured_tables)
    assert not default_db_path.exists()


def test_remove_tenant_migration_upgrades_existing_database(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-control-plane.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE datasources (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    tenant_id VARCHAR(100) NOT NULL,
                    name VARCHAR(200) NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX ix_datasources_tenant_id "
                "ON datasources (tenant_id)"
            )
        )
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('202604240001')")
        )

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(config, "head")

    inspector = inspect(create_engine(db_url))
    columns = {column["name"] for column in inspector.get_columns("datasources")}
    indexes = {index["name"] for index in inspector.get_indexes("datasources")}
    assert "tenant_id" not in columns
    assert "ix_datasources_tenant_id" not in indexes


def test_app_startup_upgrades_legacy_database(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    db_path = tmp_path / "startup-upgrade.db"
    db_url = f"sqlite:///{db_path}"
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option(
        "script_location",
        str(project_root / "src" / "adg" / "control_plane" / "migrations"),
    )
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "202604240002")

    monkeypatch.setenv("ADG_CONTROL_PLANE_DATABASE_URL", db_url)
    get_settings.cache_clear()

    try:
        with TestClient(create_app()) as client:
            response = client.get("/health")
            assert response.status_code == 200
    finally:
        get_settings.cache_clear()

    inspector = inspect(create_engine(db_url))
    resource_columns = {column["name"] for column in inspector.get_columns("resources")}
    field_columns = {column["name"] for column in inspector.get_columns("resource_fields")}
    tables = set(inspector.get_table_names())
    assert {"description", "status"}.issubset(resource_columns)
    assert {"status"}.issubset(field_columns)
    assert "datasource_tags" in tables
