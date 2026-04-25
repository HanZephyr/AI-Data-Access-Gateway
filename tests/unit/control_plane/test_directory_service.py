import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.services.directory_service import DirectoryService
from adg.shared.security import verify_api_key


def active_runtime_keys_for_user(session: Session, user_id: str) -> list[ApiKey]:
    keys = session.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.status == "active")
    ).scalars()
    return [key for key in keys if "runtime" in json.loads(key.scopes)]


def test_create_user_generates_exactly_one_runtime_key(db_session: Session) -> None:
    user, plaintext = DirectoryService(db_session).create_user(
        name="Alice",
        external_ref="u001",
        org_node_id=None,
        role_ids=[],
    )
    db_session.commit()

    runtime_keys = active_runtime_keys_for_user(db_session, user.id)

    assert plaintext.startswith("adg_")
    assert len(runtime_keys) == 1
    assert verify_api_key(plaintext, runtime_keys[0].key_hash)


def test_reset_runtime_key_revokes_old_key_immediately(db_session: Session) -> None:
    service = DirectoryService(db_session)
    user, old_plaintext = service.create_user(
        name="Alice",
        external_ref="u001",
        org_node_id=None,
        role_ids=[],
    )
    old_key = active_runtime_keys_for_user(db_session, user.id)[0]

    new_plaintext = service.reset_runtime_key(user.id)
    db_session.commit()

    db_session.refresh(old_key)
    runtime_keys = active_runtime_keys_for_user(db_session, user.id)

    assert old_key.status == "revoked"
    assert len(runtime_keys) == 1
    assert runtime_keys[0].id != old_key.id
    assert not verify_api_key(old_plaintext, runtime_keys[0].key_hash)
    assert verify_api_key(new_plaintext, runtime_keys[0].key_hash)
