import argparse
import json
from typing import Any

from adg.audit.service import AuditService
from adg.control_plane.db import create_engine_from_url, create_session_factory
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.governance import ResourceTag, Tag
from adg.control_plane.models.masking import MaskingPolicy
from adg.control_plane.models.resource import Resource, ResourceField
from adg.shared.security import hash_api_key


def seed_demo(database_url: str, *, reset: bool = True) -> dict[str, Any]:
    engine = create_engine_from_url(database_url)
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            ApiKey(
                id="demo_admin_key",
                name="Demo Admin",
                key_hash=hash_api_key("adg_admin"),
                status="active",
                scopes='["admin","runtime","internal"]',
            )
        )
        session.add(
            Datasource(
                id="demo_ds",
                tenant_id="tenant-a",
                name="Demo Warehouse",
                type="postgres",
                datasource_kind="relational",
                config_json=json.dumps(
                    {
                        "host": "localhost",
                        "port": 5432,
                        "database": "warehouse",
                        "username": "demo",
                    },
                    separators=(",", ":"),
                ),
                status="active",
            )
        )
        resource = Resource(
            id="demo_res_customers",
            tenant_id="tenant-a",
            datasource_id="demo_ds",
            parent_id=None,
            kind="relational_table",
            name="customers",
            path="warehouse.public.customers",
            display_name="customers",
            query_language="sql",
            metadata_json="{}",
        )
        session.add(resource)
        session.add(
            ResourceField(
                tenant_id="tenant-a",
                datasource_id="demo_ds",
                resource_id=resource.id,
                name="email",
                data_type="varchar",
                nullable=True,
                ordinal_position=1,
                metadata_json="{}",
            )
        )
        tag = Tag(
            id="demo_tag_pii",
            tenant_id="tenant-a",
            name="pii",
            category="classification",
            description="Personally identifiable information",
        )
        session.add(tag)
        session.add(ResourceTag(tenant_id="tenant-a", tag_id=tag.id, resource_id=resource.id))
        session.add(
            MaskingPolicy(
                tenant_id="tenant-a",
                resource_id=resource.id,
                field_name="email",
                strategy="partial",
                config_json='{"prefix":2,"suffix":3,"fill":"*"}',
                status="active",
            )
        )
        AuditService(session).record_event(
            tenant_id="tenant-a",
            user_id="demo-user",
            api_key_id="demo_admin_key",
            event_type="metadata_discovery",
            decision="allowed",
            datasource_id="demo_ds",
            resource_ids=[resource.id],
            query_id=None,
            sql_text=None,
            reason=None,
            metadata={"tool": "seed_demo"},
        )
        session.commit()

    return {
        "database_url": database_url,
        "admin_api_key": "adg_admin",
        "tenant_id": "tenant-a",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed AI Data Access Gateway demo data.")
    parser.add_argument(
        "--database-url",
        default="sqlite:///./data/adg-control-plane.db",
        help="Control-plane database URL to seed.",
    )
    parser.add_argument("--no-reset", action="store_true", help="Do not drop existing tables.")
    args = parser.parse_args()
    result = seed_demo(args.database_url, reset=not args.no_reset)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
