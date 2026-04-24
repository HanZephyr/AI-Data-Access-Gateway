from collections.abc import Iterator
from typing import cast

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.app.main import create_app
from adg.connectors.base import MetadataConnector, MetadataSnapshot
from adg.connectors.registry import get_connector_registry
from adg.control_plane.db import (
    create_engine_from_url,
    create_session_factory,
    get_session,
)
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.resource import Resource, ResourceField
from adg.shared.security import hash_api_key


class FakeConnector:
    connector_type = "fake"
    scan_count = 0

    def test_connection(self, config: dict[str, object]) -> None:
        assert config["database"] == "warehouse"

    def scan_metadata(self, config: dict[str, object]) -> MetadataSnapshot:
        type(self).scan_count += 1
        if type(self).scan_count == 1:
            return {
                "databases": [
                    {
                        "name": "warehouse",
                        "schemas": [
                            {
                                "name": "public",
                                "tables": [
                                    {
                                "name": "orders",
                                "kind": "table",
                                "columns": [
                                    {
                                        "name": "id",
                                        "data_type": "integer",
                                        "nullable": False,
                                    },
                                ],
                            }
                        ],
                                "views": [],
                            }
                        ],
                    }
                ]
            }

        return {
            "databases": [
                {
                    "name": "warehouse",
                    "schemas": [
                        {
                            "name": "analytics",
                            "tables": [],
                            "views": [
                                {
                                    "name": "daily_sales",
                                    "kind": "view",
                                    "columns": [
                                        {"name": "total", "data_type": "numeric", "nullable": True},
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }


def build_scan_client() -> tuple[TestClient, Session]:
    FakeConnector.scan_count = 0
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
        session.add(
            Datasource(
                id="ds_123",
                name="Warehouse",
                type="fake",
                datasource_kind="relational",
                config_json='{"database":"warehouse"}',
                status="active",
            )
        )
        session.commit()

    app = create_app()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    registry = get_connector_registry()
    registry.register("fake", cast(type[MetadataConnector], FakeConnector))
    return TestClient(app), session_factory()


def test_admin_datasource_test_endpoint() -> None:
    client, session = build_scan_client()
    try:
        response = client.post(
            "/admin/datasources/ds_123/test",
            headers={"X-ADG-API-Key": "adg_admin"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        session.close()


def test_admin_datasource_scan_endpoint_replaces_snapshots() -> None:
    client, session = build_scan_client()
    try:
        first = client.post(
            "/admin/datasources/ds_123/scan",
            headers={"X-ADG-API-Key": "adg_admin"},
        )
        assert first.status_code == 200
        assert first.json() == {"status": "ok", "resources": 3, "fields": 1}

        second = client.post(
            "/admin/datasources/ds_123/scan",
            headers={"X-ADG-API-Key": "adg_admin"},
        )
        assert second.status_code == 200
        assert second.json() == {"status": "ok", "resources": 3, "fields": 1}

        resources = session.execute(select(Resource).order_by(Resource.path)).scalars().all()
        fields = session.execute(select(ResourceField).order_by(ResourceField.name)).scalars().all()
        assert [resource.path for resource in resources] == [
            "warehouse",
            "warehouse.analytics",
            "warehouse.analytics.daily_sales",
        ]
        assert [field.name for field in fields] == ["total"]
    finally:
        session.close()
