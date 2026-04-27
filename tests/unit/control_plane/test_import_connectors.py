import json
from collections.abc import Iterator
from urllib import request

import pytest
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


def test_feishu_connector_fetch_uses_platform_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = FeishuImporter()
    expected = DirectoryImportBatch(
        users=[
            ImportedUserRow(
                user_name="Alice",
                org_path="Company/Finance",
                external_ref="ou_123",
                roles=["Analyst"],
            )
        ]
    )
    monkeypatch.setattr(
        connector,
        "_fetch_directory_batch",
        lambda config: expected,
    )

    batch = connector.fetch(
        {
            "delimiter": "/",
            "app_id": "cli_xxx",
            "app_secret": "secret_xxx",
            "root_department_id": "0",
        }
    )

    assert batch == expected


def test_feishu_connector_surfaces_platform_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = FeishuImporter()

    class DummyResponse:
        def __enter__(self) -> "DummyResponse":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "code": 99991663,
                    "msg": "no department permission",
                    "request_id": "20260427-demo",
                }
            ).encode("utf-8")

    monkeypatch.setattr(request, "urlopen", lambda req, timeout=20: DummyResponse())

    with pytest.raises(
        ValueError,
        match=(
            "Feishu API error 99991663: no department permission "
            r"\(request_id=20260427-demo\)"
        ),
    ):
        connector._request_json(
            "https://open.feishu.cn/open-apis/contact/v3/departments/0/children",
            token="tenant-token",
            query={"page_size": "50"},
        )


def test_feishu_connector_surfaces_unexpected_response_shape_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = FeishuImporter()
    monkeypatch.setattr(
        connector,
        "_request_json",
        lambda *args, **kwargs: {
            "code": 0,
            "msg": "success",
            "request_id": "req_demo",
            "data": {"department_infos": []},
        },
    )

    with pytest.raises(
        ValueError,
        match=(
            r"Feishu directory response did not include an items list "
            r"\(response_keys=\['code', 'data', 'msg', 'request_id'\], "
            r"payload_keys=\['department_infos'\], request_id=req_demo\)"
        ),
    ):
        connector._paginate(
            "https://open.feishu.cn/open-apis/contact/v3/departments/0/children",
            "tenant-token",
            query={"page_size": "50"},
        )


def test_feishu_connector_treats_missing_items_as_empty_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = FeishuImporter()
    monkeypatch.setattr(
        connector,
        "_request_json",
        lambda *args, **kwargs: {
            "code": 0,
            "msg": "success",
            "data": {"has_more": False},
        },
    )

    assert connector._paginate(
        "https://open.feishu.cn/open-apis/contact/v3/departments/0/children",
        "tenant-token",
        query={"page_size": "50"},
    ) == []


def test_feishu_connector_fetches_root_department_users_when_no_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = FeishuImporter()

    monkeypatch.setattr(connector, "_fetch_app_access_token", lambda *args: "tenant-token")
    monkeypatch.setattr(connector, "_fetch_departments", lambda *args: [])
    monkeypatch.setattr(
        connector,
        "_fetch_users",
        lambda token, department_ids: [
            {
                "user_id": "ou_root",
                "name": "Root User",
                "department_ids": ["0"],
                "roles": ["Admin"],
            }
        ]
        if department_ids == ["0"]
        else [],
    )

    batch = connector.fetch(
        {
            "delimiter": "/",
            "app_id": "cli_xxx",
            "app_secret": "secret_xxx",
            "root_department_id": "0",
        }
    )

    assert batch == DirectoryImportBatch(
        users=[
            ImportedUserRow(
                user_name="Root User",
                org_path=None,
                external_ref="ou_root",
                roles=["Admin"],
            )
        ]
    )


def test_feishu_connector_uses_supported_page_size_for_user_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = FeishuImporter()

    def fake_paginate(url: str, token: str, *, query: dict[str, str]) -> list[dict[str, str]]:
        assert url.endswith("/contact/v3/users/find_by_department")
        assert query["page_size"] == "50"
        assert query["department_id_type"] == "open_department_id"
        return []

    monkeypatch.setattr(connector, "_paginate", fake_paginate)

    assert connector._fetch_users("tenant-token", ["od_finance"]) == []


def test_feishu_connector_uses_root_department_id_type_for_root_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = FeishuImporter()
    seen_queries: list[dict[str, str]] = []

    def fake_paginate(
        url: str,
        token: str,
        *,
        query: dict[str, str],
    ) -> list[dict[str, object]]:
        seen_queries.append(dict(query))
        if url.endswith("/contact/v3/departments/0/children"):
            return [
                {
                    "open_department_id": "od_finance",
                    "name": "Finance",
                    "parent_department_id": "0",
                }
            ]
        if url.endswith("/contact/v3/users/find_by_department"):
            return [
                {
                    "user_id": "ou_123",
                    "name": "Alice",
                    "department_ids": ["od_finance"],
                    "roles": ["Analyst"],
                }
            ]
        return []

    monkeypatch.setattr(connector, "_fetch_app_access_token", lambda *args: "tenant-token")
    monkeypatch.setattr(connector, "_paginate", fake_paginate)

    batch = connector.fetch(
        {
            "delimiter": "/",
            "app_id": "cli_xxx",
            "app_secret": "secret_xxx",
            "root_department_id": "0",
        }
    )

    assert batch == DirectoryImportBatch(
        users=[
            ImportedUserRow(
                user_name="Alice",
                org_path="Finance",
                external_ref="ou_123",
                roles=["Analyst"],
            )
        ]
    )
    assert seen_queries[0]["department_id_type"] == "department_id"
    assert seen_queries[1]["department_id_type"] == "open_department_id"
    assert seen_queries[2]["department_id_type"] == "department_id"
    assert seen_queries[3]["department_id_type"] == "open_department_id"


def test_feishu_connector_resolves_department_paths_for_internal_and_open_ids() -> None:
    connector = FeishuImporter()

    department_paths = connector._build_department_path_map(
        {
            "items": [
                {
                    "department_id": "D001",
                    "open_department_id": "od_company",
                    "name": "Company",
                    "parent_department_id": "0",
                },
                {
                    "department_id": "D002",
                    "open_department_id": "od_finance",
                    "name": "Finance",
                    "parent_department_id": "D001",
                },
            ]
        }
    )

    assert department_paths["D001"] == "Company"
    assert department_paths["od_company"] == "Company"
    assert department_paths["D002"] == "Company/Finance"
    assert department_paths["od_finance"] == "Company/Finance"
    assert connector._resolve_org_path(
        {"department_ids": ["D002"]},
        department_paths,
    ) == "Company/Finance"
    assert connector._resolve_org_path(
        {"department_ids": ["od_finance"]},
        department_paths,
    ) == "Company/Finance"


def test_feishu_connector_infers_department_ids_from_query_when_user_payload_omits_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = FeishuImporter()

    def fake_paginate(url: str, token: str, *, query: dict[str, str]) -> list[dict[str, str]]:
        return [
            {
                "user_id": "ou_123",
                "name": "Alice",
            }
        ]

    monkeypatch.setattr(connector, "_paginate", fake_paginate)

    assert connector._fetch_users("tenant-token", ["od_finance"]) == [
        {
            "user_id": "ou_123",
            "name": "Alice",
            "department_ids": ["od_finance"],
        }
    ]


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


def test_wecom_connector_fetch_uses_platform_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = WeComImporter()
    expected = DirectoryImportBatch(
        users=[
            ImportedUserRow(
                user_name="Bob",
                org_path="Company/Finance",
                external_ref="wx_123",
                roles=["Reviewer"],
            )
        ]
    )
    monkeypatch.setattr(
        connector,
        "_fetch_directory_batch",
        lambda config: expected,
    )

    batch = connector.fetch(
        {
            "delimiter": "/",
            "corp_id": "wwcorp",
            "corp_secret": "contact-secret",
            "root_department_id": "1",
        }
    )

    assert batch == expected


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


def test_dingtalk_connector_fetch_uses_platform_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = DingTalkImporter()
    expected = DirectoryImportBatch(
        users=[
            ImportedUserRow(
                user_name="Carol",
                org_path="Company/People Ops",
                external_ref="dt_123",
                roles=["HRBP"],
            )
        ]
    )
    monkeypatch.setattr(
        connector,
        "_fetch_directory_batch",
        lambda config: expected,
    )

    batch = connector.fetch(
        {
            "delimiter": "/",
            "app_key": "ding-app-key",
            "app_secret": "ding-app-secret",
            "root_department_id": "1",
        }
    )

    assert batch == expected


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


def test_admin_returns_feishu_platform_error_details_for_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _build_importer_app()

    def fake_fetch(self: FeishuImporter, config: dict[str, object]) -> DirectoryImportBatch:
        raise ValueError("Feishu API error 99991663: no department permission")

    monkeypatch.setattr(FeishuImporter, "fetch", fake_fetch)
    response = client.post(
        "/admin/users/importers/feishu/pull",
        json={
            "mode": "preview",
            "config": {
                "delimiter": "/",
                "app_id": "cli_demo",
                "app_secret": "secret_demo",
                "root_department_id": "0",
            },
        },
        headers=_admin_auth(),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Feishu API error 99991663: no department permission"
    }


def test_admin_can_pull_from_credential_connector_config_and_preview_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _build_importer_app()

    def fake_fetch(self: WeComImporter, config: dict[str, object]) -> DirectoryImportBatch:
        assert config["corp_id"] == "wwcorp"
        assert config["corp_secret"] == "contact-secret"
        assert config["root_department_id"] == "1"
        return DirectoryImportBatch(
            users=[
                ImportedUserRow(
                    user_name="Bob",
                    org_path="Company/Finance",
                    external_ref="wx_123",
                    roles=["Reviewer"],
                )
            ]
        )

    monkeypatch.setattr(WeComImporter, "fetch", fake_fetch)
    response = client.post(
        "/admin/users/importers/wecom/pull",
        json={
            "mode": "preview",
            "config": {
                "delimiter": "/",
                "corp_id": "wwcorp",
                "corp_secret": "contact-secret",
                "root_department_id": "1",
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
