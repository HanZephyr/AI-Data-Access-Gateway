import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.directory import OrgNode, Role, UserRole
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


def test_update_user_replaces_roles_and_updates_fields(db_session: Session) -> None:
    service = DirectoryService(db_session)
    db_session.add_all([
        OrgNode(id="org_root", name="Root", path="", depth=0, status="active"),
        OrgNode(
            id="org_finance",
            name="Finance",
            parent_id="org_root",
            path="Finance",
            depth=1,
            status="active",
        ),
        Role(id="role_legacy", name="Legacy", status="active"),
        Role(id="role_admin", name="Admin", status="active"),
    ])
    user, _ = service.create_user(
        name="Alice",
        external_ref="u001",
        org_node_id=None,
        role_ids=["role_legacy"],
    )
    db_session.commit()

    role_ids = db_session.execute(
        select(UserRole.role_id).where(UserRole.user_id == user.id)
    ).scalars().all()
    assert role_ids == ["role_legacy"]

    updated = service.update_user(
        user.id,
        name="Alice Updated",
        external_ref="u002",
        org_node_id="org_finance",
        role_ids=["role_admin"],
        status="disabled",
    )
    db_session.commit()

    assert updated.name == "Alice Updated"
    assert updated.external_ref == "u002"
    assert updated.org_node_id == "org_finance"
    assert updated.status == "disabled"
    assert db_session.execute(
        select(UserRole.role_id).where(UserRole.user_id == user.id)
    ).scalars().all() == ["role_admin"]


def test_delete_user_removes_role_links_and_runtime_keys(db_session: Session) -> None:
    service = DirectoryService(db_session)
    user, _ = service.create_user(
        name="Alice",
        external_ref="u001",
        org_node_id=None,
        role_ids=[],
    )

    service.delete_user(user.id)
    db_session.commit()

    assert db_session.get(type(user), user.id) is None
    assert db_session.execute(
        select(UserRole.user_id).where(UserRole.user_id == user.id)
    ).scalars().all() == []
    assert db_session.execute(
        select(ApiKey.user_id).where(ApiKey.user_id == user.id)
    ).scalars().all() == []
