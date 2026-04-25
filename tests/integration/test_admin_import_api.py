import json
from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from adg.app.main import create_app
from adg.control_plane.db import create_engine_from_url, create_session_factory, get_session
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.directory import OrgNode, Role, User
from adg.control_plane.services.api_key_service import create_api_key
from adg.shared.security import hash_api_key


def _build_import_app() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            ApiKey(
                id="key_admin",
                name="admin",
                key_hash=hash_api_key("adg_admin"),
                status="active",
                scopes='["admin"]',
            )
        )
        session.add_all(
            [
                OrgNode(
                    id="org_company",
                    name="Company",
                    path="Company",
                    depth=0,
                    status="active",
                ),
                User(
                    id="user_existing",
                    name="Existing User",
                    external_ref="u-existing",
                    org_node_id="org_company",
                    status="active",
                ),
                Role(id="role_legacy", name="Legacy", status="active"),
            ]
        )
        create_api_key(
            session,
            name="user:Existing User",
            scopes=["runtime"],
            plaintext="adg_existing_runtime_key",
            user_id="user_existing",
        )
        session.commit()

    app = create_app()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), session_factory


def _admin_auth() -> dict[str, str]:
    return {"X-ADG-API-Key": "adg_admin"}


def _active_runtime_keys_for_user(session: Session, user_id: str) -> list[ApiKey]:
    keys = session.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.status == "active")
    ).scalars()
    return [key for key in keys if "runtime" in json.loads(key.scopes)]


def test_admin_can_preview_excel_import() -> None:
    client, _ = _build_import_app()

    response = client.post(
        "/admin/users/imports/excel/preview",
        json={
            "delimiter": "/",
            "rows": [
                {
                    "user_name": "Alice",
                    "org_path": "Company/Finance",
                    "external_ref": "u001",
                    "roles": "Analyst",
                }
            ],
        },
        headers=_admin_auth(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "users": [
            {
                "user_name": "Alice",
                "external_ref": "u001",
                "org_path": "Company/Finance",
                "roles": ["Analyst"],
                "action": "create",
            }
        ],
        "org_nodes_to_create": ["Company/Finance"],
        "roles_to_create": ["Analyst"],
        "root_org_node_required": False,
        "summary": {"create_count": 1, "update_count": 0},
    }


def test_admin_can_execute_excel_import_and_map_empty_org_path_to_root() -> None:
    client, session_factory = _build_import_app()

    response = client.post(
        "/admin/users/imports/excel/execute",
        json={
            "delimiter": "/",
            "rows": [
                {
                    "user_name": "Alice",
                    "org_path": "",
                    "external_ref": "u001",
                    "roles": "Analyst",
                }
            ],
        },
        headers=_admin_auth(),
    )

    assert response.status_code == 200
    assert response.json()["summary"] == {
        "created_users": 1,
        "updated_users": 0,
        "runtime_keys_created": 1,
    }
    assert response.json()["root_org_node_created"] is True

    with session_factory() as session:
        user = session.execute(select(User).where(User.external_ref == "u001")).scalar_one()
        root = session.execute(select(OrgNode).where(OrgNode.path == "")).scalar_one()
        analyst = session.execute(select(Role).where(Role.name == "Analyst")).scalar_one()
        active_keys = _active_runtime_keys_for_user(session, user.id)

        assert user.org_node_id == root.id
        assert analyst.status == "active"
        assert len(active_keys) == 1


def test_admin_execute_updates_existing_user_without_rotating_runtime_key() -> None:
    client, session_factory = _build_import_app()

    with session_factory() as session:
        old_key = _active_runtime_keys_for_user(session, "user_existing")[0]
        old_key_id = old_key.id
        old_key_hash = old_key.key_hash

    response = client.post(
        "/admin/users/imports/excel/execute",
        json={
            "delimiter": "/",
            "rows": [
                {
                    "user_name": "Existing User Updated",
                    "org_path": "Company/Finance",
                    "external_ref": "u-existing",
                    "roles": "Analyst,Reviewer",
                }
            ],
        },
        headers=_admin_auth(),
    )

    assert response.status_code == 200
    assert response.json()["summary"] == {
        "created_users": 0,
        "updated_users": 1,
        "runtime_keys_created": 0,
    }

    with session_factory() as session:
        user = session.execute(select(User).where(User.external_ref == "u-existing")).scalar_one()
        finance = session.execute(
            select(OrgNode).where(OrgNode.path == "Company/Finance")
        ).scalar_one()
        active_keys = _active_runtime_keys_for_user(session, user.id)
        role_names = set(
            session.execute(select(Role.name).order_by(Role.name)).scalars()
        )

        assert user.name == "Existing User Updated"
        assert user.org_node_id == finance.id
        assert len(active_keys) == 1
        assert active_keys[0].id == old_key_id
        assert active_keys[0].key_hash == old_key_hash
        assert {"Analyst", "Reviewer"} <= role_names
