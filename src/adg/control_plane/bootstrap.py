import argparse
import json
from typing import Any

from adg.control_plane.db import create_engine_from_url, create_session_factory
from adg.control_plane.models.base import Base
from adg.control_plane.services.api_key_service import create_api_key


def bootstrap_admin_api_key(database_url: str, *, name: str = "Bootstrap Admin") -> dict[str, Any]:
    """Create a one-time admin API key for a control-plane database."""

    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        record, plaintext = create_api_key(session, name=name, scopes=["admin"])
        session.commit()
        session.refresh(record)

    return {
        "database_url": database_url,
        "id": record.id,
        "name": record.name,
        "api_key": plaintext,
    }


def main() -> None:
    """Create one bootstrap admin key and print it as JSON for operators."""

    parser = argparse.ArgumentParser(description="Bootstrap an admin API key for ADG.")
    parser.add_argument(
        "--database-url",
        default="sqlite:///./data/adg-control-plane.db",
        help="Control-plane database URL to initialize.",
    )
    parser.add_argument(
        "--name",
        default="Bootstrap Admin",
        help="Display name stored alongside the bootstrap API key.",
    )
    args = parser.parse_args()
    print(json.dumps(bootstrap_admin_api_key(args.database_url, name=args.name), indent=2))


if __name__ == "__main__":
    main()
