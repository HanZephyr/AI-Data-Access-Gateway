from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_initial_migration_creates_foundation_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "control-plane.db"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(config, "head")

    engine = create_engine(db_url)
    tables = set(inspect(engine).get_table_names())
    assert {"api_keys", "audit_events", "alembic_version"}.issubset(tables)
