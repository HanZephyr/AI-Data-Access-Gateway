"""Runtime helpers for keeping the control-plane schema current."""

from pathlib import Path
from threading import Lock

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

_migration_lock = Lock()
_migrated_urls: set[str] = set()


def ensure_control_plane_schema(database_url: str) -> None:
    """Upgrade the configured control-plane database to the latest Alembic revision."""

    with _migration_lock:
        if database_url in _migrated_urls:
            return

        _ensure_sqlite_directory(database_url)
        project_root = Path(__file__).resolve().parents[4]
        config = Config(str(project_root / "alembic.ini"))
        config.set_main_option(
            "script_location",
            str(project_root / "src" / "adg" / "control_plane" / "migrations"),
        )
        config.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(config, "head")
        _migrated_urls.add(database_url)


def _ensure_sqlite_directory(database_url: str) -> None:
    """Create the parent directory for SQLite files before Alembic opens them."""

    if not database_url.startswith("sqlite"):
        return

    url = make_url(database_url)
    if url.database and url.database != ":memory:":
        Path(url.database).expanduser().parent.mkdir(parents=True, exist_ok=True)
