from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from adg.app.main import create_app
from adg.control_plane.db import create_engine_from_url, create_session_factory, get_session
from adg.control_plane.imports.connectors.base import DirectoryImportBatch
from adg.control_plane.imports.connectors.dingtalk import DingTalkImporter
from adg.control_plane.imports.connectors.feishu import FeishuImporter
from adg.control_plane.imports.connectors.registry import CONNECTOR_REGISTRY
from adg.control_plane.imports.connectors.wecom import WeComImporter
from adg.control_plane.imports.models import ImportedUserRow
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.shared.security import hash_api_key


def sample_feishu_response() -> dict[str, object]:
    return {
        "users": [
            {
                "user_id": "ou_123",
                "name": "Alice",
                "department_path": ["Company", "Finance"],
                "roles": ["Analyst"],
            }
        ]
    }


def sample_feishu_departments_response() -> dict[str, object]:
    return {
        "data": {
            "items": [
                {
                    "open_department_id": "od_company",
                    "name": "Company",
                    "parent_department_id": "0",
                },
                {
                    "open_department_id": "od_finance",
                    "name": "Finance",
                    "parent_department_id": "od_company",
                },
            ]
        }
    }


def sample_feishu_users_response() -> dict[str, object]:
    return {
        "data": {
            "items": [
                {
                    "user_id": "ou_123",
                    "name": "Alice",
                    "department_ids": ["od_finance"],
                    "roles": ["Analyst"],
                }
            ]
        }
    }


def sample_wecom_response() -> dict[str, object]:
    return {
        "department_names": {"1": "Company", "2": "Finance"},
        "users": [
            {
                "userid": "wx_123",
                "name": "Bob",
                "department": ["1", "2"],
                "extattr": {"roles": ["Reviewer", "Reviewer"]},
            }
        ],
    }


def sample_wecom_departments_response() -> dict[str, object]:
    return {
        "department": [
            {"id": 1, "name": "Company", "parentid": 0},
            {"id": 2, "name": "Finance", "parentid": 1},
        ]
    }


def sample_wecom_users_response() -> dict[str, object]:
    return {
        "userlist": [
            {
                "userid": "wx_123",
                "name": "Bob",
                "department": [1, 2],
                "extattr": {"roles": ["Reviewer", "Reviewer"]},
            }
        ]
    }


def sample_dingtalk_response() -> dict[str, object]:
    return {
        "result": {
            "users": [
                {
                    "userid": "dt_123",
                    "name": "Carol",
                    "dept_path": "Company/People Ops",
                    "role_list": [{"name": "HRBP"}],
                }
            ]
        }
    }


def sample_dingtalk_departments_response() -> dict[str, object]:
    return {
        "result": [
            {"dept_id": 1, "name": "Company", "parent_id": 0},
            {"dept_id": 2, "name": "People Ops", "parent_id": 1},
        ]
    }


def sample_dingtalk_users_response() -> dict[str, object]:
    return {
        "result": {
            "list": [
                {
                    "userid": "dt_123",
                    "name": "Carol",
                    "dept_id_list": [2],
                    "role_list": [{"name": "HRBP"}],
                }
            ]
        }
    }


def _build_importer_app() -> TestClient:
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
        session.commit()

    app = create_app()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _admin_auth() -> dict[str, str]:
    return {"X-ADG-API-Key": "adg_admin"}


def test_feishu_connector_normalizes_users_and_org_paths() -> None:
    connector = FeishuImporter()

    batch = connector.normalize(sample_feishu_response())

    assert batch == DirectoryImportBatch(
        users=[
            ImportedUserRow(
                user_name="Alice",
                org_path="Company/Finance",
                external_ref="ou_123",
                roles=["Analyst"],
            )
        ]
    )


def test_feishu_connector_fetch_accepts_structured_platform_config() -> None:
    connector = FeishuImporter()

    batch = connector.fetch(
        {
            "delimiter": "/",
            "departments_payload": sample_feishu_departments_response(),
            "users_payload": sample_feishu_users_response(),
        }
    )

    assert batch == DirectoryImportBatch(
        users=[
            ImportedUserRow(
                user_name="Alice",
                org_path="Company/Finance",
                external_ref="ou_123",
                roles=["Analyst"],
            )
        ]
    )


def test_wecom_connector_fetch_returns_unified_batch() -> None:
    connector = WeComImporter()

    batch = connector.fetch({"payload": sample_wecom_response()})

    assert batch == DirectoryImportBatch(
        users=[
            ImportedUserRow(
                user_name="Bob",
                org_path="Company/Finance",
                external_ref="wx_123",
                roles=["Reviewer"],
            )
        ]
    )


def test_wecom_connector_fetch_accepts_structured_platform_config() -> None:
    connector = WeComImporter()

    batch = connector.fetch(
        {
            "delimiter": "/",
            "departments_payload": sample_wecom_departments_response(),
            "users_payload": sample_wecom_users_response(),
        }
    )

    assert batch == DirectoryImportBatch(
        users=[
            ImportedUserRow(
                user_name="Bob",
                org_path="Company/Finance",
                external_ref="wx_123",
                roles=["Reviewer"],
            )
        ]
    )


def test_dingtalk_connector_fetch_returns_unified_batch() -> None:
    connector = DingTalkImporter()

    batch = connector.fetch({"payload": sample_dingtalk_response()})

    assert batch == DirectoryImportBatch(
        users=[
            ImportedUserRow(
                user_name="Carol",
                org_path="Company/People Ops",
                external_ref="dt_123",
                roles=["HRBP"],
            )
        ]
    )


def test_dingtalk_connector_fetch_accepts_structured_platform_config() -> None:
    connector = DingTalkImporter()

    batch = connector.fetch(
        {
            "delimiter": "/",
            "departments_payload": sample_dingtalk_departments_response(),
            "users_payload": sample_dingtalk_users_response(),
        }
    )

    assert batch == DirectoryImportBatch(
        users=[
            ImportedUserRow(
                user_name="Carol",
                org_path="Company/People Ops",
                external_ref="dt_123",
                roles=["HRBP"],
            )
        ]
    )


def test_connector_registry_exposes_supported_platforms() -> None:
    assert set(CONNECTOR_REGISTRY) == {"feishu", "wecom", "dingtalk"}


def test_admin_can_pull_from_connector_and_preview_batch() -> None:
    client = _build_importer_app()

    response = client.post(
        "/admin/users/importers/feishu/pull",
        json={
            "mode": "preview",
            "config": {"payload": sample_feishu_response()},
        },
        headers=_admin_auth(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "users": [
            {
                "user_name": "Alice",
                "external_ref": "ou_123",
                "org_path": "Company/Finance",
                "roles": ["Analyst"],
                "action": "create",
            }
        ],
        "org_nodes_to_create": ["Company", "Company/Finance"],
        "roles_to_create": ["Analyst"],
        "root_org_node_required": False,
        "summary": {"create_count": 1, "update_count": 0},
    }


def test_admin_can_pull_from_structured_connector_config_and_preview_batch() -> None:
    client = _build_importer_app()

    response = client.post(
        "/admin/users/importers/wecom/pull",
        json={
            "mode": "preview",
            "config": {
                "delimiter": "/",
                "departments_payload": sample_wecom_departments_response(),
                "users_payload": sample_wecom_users_response(),
            },
        },
        headers=_admin_auth(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "users": [
            {
                "user_name": "Bob",
                "external_ref": "wx_123",
                "org_path": "Company/Finance",
                "roles": ["Reviewer"],
                "action": "create",
            }
        ],
        "org_nodes_to_create": ["Company", "Company/Finance"],
        "roles_to_create": ["Reviewer"],
        "root_org_node_required": False,
        "summary": {"create_count": 1, "update_count": 0},
    }
