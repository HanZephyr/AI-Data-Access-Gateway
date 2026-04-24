from pathlib import Path

from sqlalchemy import text

from adg.control_plane.db import create_engine_from_url, create_session_factory


def test_create_session_factory_executes_sql() -> None:
    engine = create_engine_from_url("sqlite:///:memory:")
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        result = session.execute(text("select 1")).scalar_one()

    assert result == 1


def test_create_engine_from_url_creates_sqlite_parent_directory(tmp_path: Path) -> None:
    database_path = tmp_path / "missing" / "control-plane.db"
    engine = create_engine_from_url(f"sqlite:///{database_path}")

    with engine.connect() as connection:
        result = connection.execute(text("select 1")).scalar_one()

    assert result == 1
    assert database_path.exists()
