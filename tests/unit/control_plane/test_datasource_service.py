import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.control_plane.models import Base
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.resource import Resource, ResourceField
from adg.control_plane.services.datasource_service import DatasourceService
from adg.control_plane.services.metadata_scan_service import MetadataScanService


def test_datasource_and_snapshot_models_are_registered() -> None:
    assert Datasource.__tablename__ == "datasources"
    assert Resource.__tablename__ == "resources"
    assert ResourceField.__tablename__ == "resource_fields"
    assert "datasources" in Base.metadata.tables
    assert "resources" in Base.metadata.tables
    assert "resource_fields" in Base.metadata.tables


def test_datasource_service_crud_cycle(db_session: Session) -> None:
    service = DatasourceService(db_session)

    created = service.create_datasource(
        tenant_id="default",
        name="Warehouse",
        connector_type="postgres",
        config={"host": "localhost", "port": 5432, "database": "warehouse"},
    )
    db_session.commit()

    assert created.name == "Warehouse"
    assert json.loads(created.config_json)["database"] == "warehouse"
    assert [item.id for item in service.list_datasources()] == [created.id]

    updated = service.update_datasource(
        datasource_id=created.id,
        name="Warehouse Replica",
        status="disabled",
        config={"host": "localhost", "port": 5432, "database": "replica"},
    )
    db_session.commit()

    assert updated.name == "Warehouse Replica"
    assert updated.status == "disabled"
    assert json.loads(updated.config_json)["database"] == "replica"

    service.delete_datasource(created.id)
    db_session.commit()

    assert service.list_datasources() == []


def test_metadata_scan_service_replaces_prior_snapshots(db_session: Session) -> None:
    datasource_service = DatasourceService(db_session)
    datasource = datasource_service.create_datasource(
        tenant_id="default",
        name="Warehouse",
        connector_type="postgres",
        config={"database": "warehouse"},
    )
    db_session.commit()

    scan_service = MetadataScanService(db_session)
    first_snapshot = {
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
                                    {"name": "id", "data_type": "integer", "nullable": False},
                                ],
                            }
                        ],
                        "views": [],
                    }
                ],
            }
        ]
    }
    second_snapshot = {
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

    first_counts = scan_service.replace_snapshot(datasource=datasource, snapshot=first_snapshot)
    db_session.commit()
    assert first_counts == {"resources": 3, "fields": 1}

    second_counts = scan_service.replace_snapshot(datasource=datasource, snapshot=second_snapshot)
    db_session.commit()
    assert second_counts == {"resources": 3, "fields": 1}

    resources = db_session.execute(select(Resource).order_by(Resource.path)).scalars().all()
    fields = db_session.execute(select(ResourceField).order_by(ResourceField.name)).scalars().all()

    assert [resource.path for resource in resources] == [
        "warehouse",
        "warehouse.analytics",
        "warehouse.analytics.daily_sales",
    ]
    assert resources[-1].kind == "relational_view"
    assert [field.name for field in fields] == ["total"]
