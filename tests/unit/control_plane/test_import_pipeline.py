import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.control_plane.imports.excel import normalize_excel_import_rows
from adg.control_plane.imports.models import ImportedUserRow
from adg.control_plane.imports.pipeline import execute_excel_import, preview_excel_import
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.directory import OrgNode, Role, User, UserRole
from adg.control_plane.services.api_key_service import create_api_key


def _active_runtime_keys_for_user(session: Session, user_id: str) -> list[ApiKey]:
    keys = session.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.status == "active")
    ).scalars()
    return [key for key in keys if "runtime" in json.loads(key.scopes)]


def test_normalize_excel_rows_trims_org_segments_and_roles() -> None:
    rows = normalize_excel_import_rows(
        [
            {
                "user_name": "Alice",
                "org_path": " Company / Finance / APAC ",
                "external_ref": "u001",
                "roles": " Analyst, Reviewer , Analyst ",
            }
        ],
        delimiter="/",
    )

    assert rows == [
        ImportedUserRow(
            user_name="Alice",
            org_path="Company/Finance/APAC",
            external_ref="u001",
            roles=["Analyst", "Reviewer"],
        )
    ]


def test_excel_preview_creates_missing_org_nodes_and_roles(db_session: Session) -> None:
    result = preview_excel_import(
        db_session,
        rows=[
            {
                "user_name": "Alice",
                "org_path": "Company/Finance",
                "external_ref": "u001",
                "roles": "Analyst",
            }
        ],
        delimiter="/",
    )

    assert result.org_nodes_to_create == ["Company", "Company/Finance"]
    assert result.roles_to_create == ["Analyst"]
    assert result.summary == {"create_count": 1, "update_count": 0}
    assert result.users == [
        {
            "user_name": "Alice",
            "external_ref": "u001",
            "org_path": "Company/Finance",
            "roles": ["Analyst"],
            "action": "create",
        }
    ]


def test_execute_excel_import_creates_missing_org_nodes_roles_and_runtime_key(
    db_session: Session,
) -> None:
    result = execute_excel_import(
        db_session,
        rows=[
            {
                "user_name": "Alice",
                "org_path": "Company/Finance",
                "external_ref": "u001",
                "roles": "Analyst",
            }
        ],
        delimiter="/",
    )

    created_user = db_session.execute(select(User).where(User.external_ref == "u001")).scalar_one()
    company = db_session.execute(select(OrgNode).where(OrgNode.path == "Company")).scalar_one()
    finance = db_session.execute(
        select(OrgNode).where(OrgNode.path == "Company/Finance")
    ).scalar_one()
    analyst = db_session.execute(select(Role).where(Role.name == "Analyst")).scalar_one()
    user_roles = list(
        db_session.execute(select(UserRole).where(UserRole.user_id == created_user.id)).scalars()
    )
    runtime_keys = _active_runtime_keys_for_user(db_session, created_user.id)

    assert company.parent_id is None
    assert finance.parent_id == company.id
    assert created_user.org_node_id == finance.id
    assert {user_role.role_id for user_role in user_roles} == {analyst.id}
    assert len(runtime_keys) == 1
    assert result.summary == {
        "created_users": 1,
        "updated_users": 0,
        "runtime_keys_created": 1,
    }


def test_empty_org_path_maps_user_to_root(db_session: Session) -> None:
    result = execute_excel_import(
        db_session,
        rows=[
            {
                "user_name": "Alice",
                "org_path": "",
                "external_ref": "u001",
                "roles": "",
            }
        ],
        delimiter="/",
    )

    loaded_user = db_session.execute(select(User).where(User.external_ref == "u001")).scalar_one()
    root = db_session.execute(select(OrgNode).where(OrgNode.path == "")).scalar_one()

    assert loaded_user.org_node_id == root.id
    assert result.root_org_node_created is True


def test_execute_excel_import_updates_existing_user_without_rotating_runtime_key(
    db_session: Session,
) -> None:
    company = OrgNode(id="org_company", name="Company", path="Company", depth=0, status="active")
    finance = OrgNode(
        id="org_finance",
        name="Finance",
        parent_id="org_company",
        path="Company/Finance",
        depth=1,
        status="active",
    )
    legacy_role = Role(id="role_legacy", name="Legacy", status="active")
    existing_user = User(
        id="user_existing",
        name="Existing User",
        external_ref="u-existing",
        org_node_id="org_company",
        status="active",
    )
    db_session.add_all([company, finance, legacy_role, existing_user])
    db_session.add(UserRole(user_id="user_existing", role_id="role_legacy"))
    existing_key, _ = create_api_key(
        db_session,
        name="user:Existing User",
        scopes=["runtime"],
        plaintext="adg_existing_runtime_key",
        user_id="user_existing",
    )
    db_session.flush()
    existing_key_id = existing_key.id
    existing_key_hash = existing_key.key_hash

    result = execute_excel_import(
        db_session,
        rows=[
            {
                "user_name": "Alice Updated",
                "org_path": "Company/Finance",
                "external_ref": "u-existing",
                "roles": "Analyst,Reviewer",
            }
        ],
        delimiter="/",
    )

    updated_user = db_session.execute(
        select(User).where(User.external_ref == "u-existing")
    ).scalar_one()
    active_keys = _active_runtime_keys_for_user(db_session, updated_user.id)
    role_names = set(
        db_session.execute(
            select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(
                UserRole.user_id == updated_user.id
            )
        ).scalars()
    )

    assert updated_user.name == "Alice Updated"
    assert updated_user.org_node_id == finance.id
    assert len(active_keys) == 1
    assert active_keys[0].id == existing_key_id
    assert active_keys[0].key_hash == existing_key_hash
    assert role_names == {"Analyst", "Reviewer"}
    assert result.summary == {
        "created_users": 0,
        "updated_users": 1,
        "runtime_keys_created": 0,
    }
