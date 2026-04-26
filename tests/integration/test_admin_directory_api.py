import json
from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from adg.app.main import create_app
from adg.control_plane.db import create_engine_from_url, create_session_factory, get_session
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.directory import OrgNode, Role, User, UserRole
from adg.control_plane.services.api_key_service import create_api_key as create_api_key_record
from adg.shared.security import hash_api_key, verify_api_key


def build_directory_app() -> tuple[TestClient, sessionmaker[Session]]:
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
                OrgNode(
                    id="org_finance",
                    name="Finance",
                    parent_id="org_company",
                    path="Company/Finance",
                    depth=1,
                    status="active",
                ),
                Role(id="role_admin", name="Admin", status="active"),
                Role(id="role_finance", name="Finance", status="active"),
                User(
                    id="user_1",
                    name="Existing User",
                    external_ref="u-existing",
                    org_node_id="org_finance",
                    status="active",
                ),
                UserRole(user_id="user_1", role_id="role_finance"),
            ]
        )
        create_api_key_record(
            session,
            name="user:Existing User",
            scopes=["runtime"],
            plaintext="adg_existing_runtime_key",
            user_id="user_1",
        )
        session.commit()

    app = create_app()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), session_factory


def admin_auth() -> dict[str, str]:
    return {"X-ADG-API-Key": "adg_admin"}


def test_admin_can_create_user_and_receive_plaintext_key() -> None:
    client, session_factory = build_directory_app()

    response = client.post(
        "/admin/users",
        json={
            "name": "Alice",
            "external_ref": "u001",
            "org_node_id": "org_finance",
            "role_ids": ["role_finance"],
        },
        headers=admin_auth(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Alice"
    assert body["external_ref"] == "u001"
    assert body["org_node_id"] == "org_finance"
    assert body["role_ids"] == ["role_finance"]
    assert body["status"] == "active"
    assert body["api_key"].startswith("adg_")

    with session_factory() as session:
        created_user = session.get(User, body["id"])
        runtime_keys = list(
            session.execute(
                select(ApiKey).where(ApiKey.user_id == body["id"], ApiKey.status == "active")
            ).scalars()
        )

        assert created_user is not None
        assert len(runtime_keys) == 1
        assert json.loads(runtime_keys[0].scopes) == ["runtime"]
        assert verify_api_key(body["api_key"], runtime_keys[0].key_hash)


def test_admin_can_reset_user_key() -> None:
    client, session_factory = build_directory_app()

    response = client.post("/admin/users/user_1/reset-key", headers=admin_auth())

    assert response.status_code == 200
    body = response.json()
    assert body["api_key"].startswith("adg_")

    with session_factory() as session:
        user_keys = list(
            session.execute(select(ApiKey).where(ApiKey.user_id == "user_1")).scalars()
        )
        revoked_keys = [key for key in user_keys if key.status == "revoked"]
        active_keys = [key for key in user_keys if key.status == "active"]

        assert len(revoked_keys) == 1
        assert len(active_keys) == 1
        assert not verify_api_key("adg_existing_runtime_key", active_keys[0].key_hash)
        assert verify_api_key(body["api_key"], active_keys[0].key_hash)


def test_admin_can_list_users_with_org_path_roles_and_runtime_key_status() -> None:
    client, _ = build_directory_app()

    response = client.get("/admin/users", headers=admin_auth())

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "user_1",
            "name": "Existing User",
            "external_ref": "u-existing",
            "org_node_id": "org_finance",
            "org_path": "Company/Finance",
            "role_ids": ["role_finance"],
            "role_names": ["Finance"],
            "status": "active",
            "runtime_key_status": "active",
        }
    ]


def test_admin_can_list_roles_and_org_nodes() -> None:
    client, _ = build_directory_app()

    roles_response = client.get("/admin/roles", headers=admin_auth())
    org_nodes_response = client.get("/admin/org-nodes", headers=admin_auth())

    assert roles_response.status_code == 200
    assert roles_response.json() == [
        {
            "id": "role_admin",
            "name": "Admin",
            "description": None,
            "status": "active",
        },
        {
            "id": "role_finance",
            "name": "Finance",
            "description": None,
            "status": "active",
        },
    ]
    assert org_nodes_response.status_code == 200
    assert org_nodes_response.json() == [
        {
            "id": "org_company",
            "name": "Company",
            "code": None,
            "parent_id": None,
            "path": "Company",
            "depth": 0,
            "status": "active",
            "direct_user_count": 0,
            "direct_user_names": [],
        },
        {
            "id": "org_finance",
            "name": "Finance",
            "code": None,
            "parent_id": "org_company",
            "path": "Company/Finance",
            "depth": 1,
            "status": "active",
            "direct_user_count": 1,
            "direct_user_names": ["Existing User"],
        },
    ]


def test_admin_can_create_and_update_roles() -> None:
    client, _ = build_directory_app()

    create_response = client.post(
        "/admin/roles",
        json={
            "name": "Analyst",
            "description": "Can review finance datasets",
        },
        headers=admin_auth(),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Analyst"
    assert created["description"] == "Can review finance datasets"
    assert created["status"] == "active"

    update_response = client.patch(
        f"/admin/roles/{created['id']}",
        json={
            "description": "Can review finance and audit datasets",
            "status": "disabled",
        },
        headers=admin_auth(),
    )

    assert update_response.status_code == 200
    assert update_response.json() == {
        "id": created["id"],
        "name": "Analyst",
        "description": "Can review finance and audit datasets",
        "status": "disabled",
    }

    list_response = client.get("/admin/roles", headers=admin_auth())

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": "role_admin",
            "name": "Admin",
            "description": None,
            "status": "active",
        },
        {
            "id": created["id"],
            "name": "Analyst",
            "description": "Can review finance and audit datasets",
            "status": "disabled",
        },
        {
            "id": "role_finance",
            "name": "Finance",
            "description": None,
            "status": "active",
        },
    ]


def test_admin_can_create_update_and_delete_org_nodes() -> None:
    client, session_factory = build_directory_app()

    create_response = client.post(
        "/admin/org-nodes",
        json={
            "name": "Platform",
            "parent_id": "org_company",
        },
        headers=admin_auth(),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Platform"
    assert created["path"] == "Company/Platform"
    assert created["depth"] == 1

    update_response = client.patch(
        f"/admin/org-nodes/{created['id']}",
        json={
            "name": "Core Platform",
        },
        headers=admin_auth(),
    )

    assert update_response.status_code == 200
    assert update_response.json()["path"] == "Company/Core Platform"

    with session_factory() as session:
        created_node = session.get(OrgNode, created["id"])
        assert created_node is not None
        assert created_node.path == "Company/Core Platform"

    delete_response = client.delete(
        f"/admin/org-nodes/{created['id']}",
        headers=admin_auth(),
    )

    assert delete_response.status_code == 204


def test_org_nodes_include_direct_user_names_for_leaf_nodes() -> None:
    client, _ = build_directory_app()

    response = client.get("/admin/org-nodes", headers=admin_auth())

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "org_company",
            "name": "Company",
            "code": None,
            "parent_id": None,
            "path": "Company",
            "depth": 0,
            "status": "active",
            "direct_user_count": 0,
            "direct_user_names": [],
        },
        {
            "id": "org_finance",
            "name": "Finance",
            "code": None,
            "parent_id": "org_company",
            "path": "Company/Finance",
            "depth": 1,
            "status": "active",
            "direct_user_count": 1,
            "direct_user_names": ["Existing User"],
        },
    ]
