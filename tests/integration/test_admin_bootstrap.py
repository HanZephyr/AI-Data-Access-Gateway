import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from adg.control_plane.bootstrap import bootstrap_admin_api_key
from adg.control_plane.models.api_key import ApiKey
from adg.shared.security import verify_api_key


def test_bootstrap_admin_api_key_creates_random_admin_credentials(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'bootstrap.db'}"

    result = bootstrap_admin_api_key(database_url, name="Bootstrap Admin")

    engine = create_engine(database_url)
    session_factory = sessionmaker(bind=engine, future=True)
    with session_factory() as session:
        stored = session.execute(select(ApiKey)).scalar_one()

    assert result["api_key"].startswith("adg_")
    assert result["name"] == "Bootstrap Admin"
    assert verify_api_key(result["api_key"], stored.key_hash)
    assert json.loads(stored.scopes) == ["admin"]
