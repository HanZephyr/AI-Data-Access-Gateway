from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from adg.audit.models import AuditEvent
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.governance import ResourceTag, Tag
from adg.control_plane.models.masking import MaskingPolicy
from adg.control_plane.models.resource import Resource, ResourceField
from examples.seed_demo import seed_demo


def test_seed_demo_creates_console_ready_data(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'demo.db'}"

    result = seed_demo(database_url)

    engine = create_engine(database_url)
    session_factory = sessionmaker(bind=engine, future=True)
    with session_factory() as session:
        assert session.get(ApiKey, "demo_admin_key") is not None
        assert session.get(Datasource, "demo_ds") is not None
        assert session.get(Resource, "demo_res_customers") is not None
        assert session.execute(select(ResourceField)).scalar_one().name == "email"
        assert session.execute(select(Tag)).scalar_one().name == "pii"
        assert session.execute(select(ResourceTag)).scalar_one().resource_id == "demo_res_customers"
        assert session.execute(select(MaskingPolicy)).scalar_one().strategy == "partial"
        assert session.execute(select(AuditEvent)).scalar_one().event_type == "metadata_discovery"

    assert result["admin_api_key"] == "adg_admin"
