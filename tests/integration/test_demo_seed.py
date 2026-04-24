import json
from pathlib import Path
from typing import Any
from uuid import UUID

from examples.seed_demo import seed_demo
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from adg.audit.models import AuditEvent
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.governance import ResourceTag, Tag
from adg.control_plane.models.masking import MaskingPolicy
from adg.control_plane.models.resource import Resource, ResourceField
from adg.shared.security import verify_api_key


def assert_uuidv7(value: str) -> None:
    parsed = UUID(value)
    assert str(parsed) == value
    assert parsed.version == 7


def test_seed_demo_creates_console_ready_data(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'demo.db'}"

    result = seed_demo(database_url)

    engine = create_engine(database_url)
    session_factory = sessionmaker(bind=engine, future=True)
    with session_factory() as session:
        api_key = session.execute(select(ApiKey)).scalar_one()
        datasource = session.execute(select(Datasource)).scalar_one()
        resources = session.execute(select(Resource).order_by(Resource.path)).scalars().all()
        fields = (
            session.execute(select(ResourceField).order_by(ResourceField.ordinal_position))
            .scalars()
            .all()
        )
        tag = session.execute(select(Tag)).scalar_one()
        binding = session.execute(select(ResourceTag)).scalar_one()
        masking = session.execute(select(MaskingPolicy)).scalar_one()
        audit = session.execute(select(AuditEvent)).scalar_one()
        resource = resources[-1]
        field = fields[-1]

        records: list[Any] = [
            api_key,
            datasource,
            *resources,
            *fields,
            tag,
            binding,
            masking,
            audit,
        ]
        for record in records:
            assert_uuidv7(record.id)

        assert api_key.name == "Demo Admin"
        assert datasource.name == "Demo Warehouse"
        assert [item.kind for item in resources] == ["database", "schema", "relational_table"]
        assert [item.parent_id for item in resources] == [None, resources[0].id, resources[1].id]
        assert resource.name == "customers"
        assert resource.path == "warehouse.public.customers"
        assert [item.name for item in fields] == ["id", "email"]
        assert field.name == "email"
        assert field.resource_id == resource.id
        assert tag.name == "pii"
        assert binding.resource_id == resource.id
        assert binding.tag_id == tag.id
        assert masking.resource_id == resource.id
        assert masking.strategy == "partial"
        assert audit.datasource_id == datasource.id
        assert json.loads(audit.resource_ids_json) == [resource.id]
        assert audit.event_type == "metadata_discovery"

    assert result["admin_api_key"].startswith("adg_")
    assert result["admin_api_key"] != "adg_admin"
    assert verify_api_key(result["admin_api_key"], api_key.key_hash)
    assert "tenant_id" not in result
