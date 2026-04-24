import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.services.api_key_service import create_api_key
from adg.shared.security import verify_api_key


def test_create_api_key_generates_random_plaintext_and_persists_hash(db_session: Session) -> None:
    record, plaintext = create_api_key(
        db_session,
        name="Initial Admin",
        scopes=["admin"],
    )
    db_session.commit()

    stored = db_session.execute(select(ApiKey).where(ApiKey.id == record.id)).scalar_one()

    assert plaintext.startswith("adg_")
    assert verify_api_key(plaintext, stored.key_hash)
    assert json.loads(stored.scopes) == ["admin"]
