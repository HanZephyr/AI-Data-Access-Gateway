import json
from datetime import datetime

from sqlalchemy.orm import Session

from adg.control_plane.models.api_key import ApiKey
from adg.shared.security import generate_api_key, hash_api_key


def create_api_key(
    session: Session,
    *,
    name: str,
    scopes: list[str],
    expires_at: datetime | None = None,
    plaintext: str | None = None,
    user_id: str | None = None,
) -> tuple[ApiKey, str]:
    """Create an API key record and return the raw key exactly once to the caller."""

    raw_key = plaintext or generate_api_key()
    api_key = ApiKey(
        name=name,
        key_hash=hash_api_key(raw_key),
        user_id=user_id,
        status="active",
        scopes=json.dumps(scopes, separators=(",", ":")),
        expires_at=expires_at,
    )
    session.add(api_key)
    session.flush()
    return api_key, raw_key
