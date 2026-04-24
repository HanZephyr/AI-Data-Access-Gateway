import argparse
import json
from typing import Any

from adg.audit.service import AuditService
from adg.control_plane.db import create_engine_from_url, create_session_factory
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.base import Base
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.governance import ResourceTag, Tag
from adg.control_plane.models.masking import MaskingPolicy
from adg.control_plane.models.resource import Resource, ResourceField
from adg.shared.security import hash_api_key


def seed_demo(database_url: str, *, reset: bool = True) -> dict[str, Any]:
    """Create a small console-ready dataset for local demos and screenshots."""

    engine = create_engine_from_url(database_url)
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        # The demo key intentionally carries all scopes so quickstart flows stay simple.
        api_key = ApiKey(
            name="Demo Admin",
            key_hash=hash_api_key("adg_admin"),
            status="active",
            scopes='["admin","runtime","internal"]',
        )
        session.add(api_key)
        datasource = Datasource(
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
        session.add(datasource)
        session.flush()
        database = Resource(
            datasource_id=datasource.id,
            parent_id=None,
            kind="database",
            name="warehouse",
            path="warehouse",
            display_name="warehouse",
            description="Demo analytical warehouse used by the gateway examples.",
            query_language="sql",
            status="active",
            metadata_json="{}",
        )
        session.add(database)
        session.flush()
        schema = Resource(
            datasource_id=datasource.id,
            parent_id=database.id,
            kind="schema",
            name="public",
            path="warehouse.public",
            display_name="public",
            description="Public schema exposed to analytics users.",
            query_language="sql",
            status="active",
            metadata_json="{}",
        )
        session.add(schema)
        session.flush()
        # Seed one table resource with PII-like fields so masking and catalog UI have useful data.
        resource = Resource(
            datasource_id=datasource.id,
            parent_id=schema.id,
            kind="relational_table",
            name="customers",
            path="warehouse.public.customers",
            display_name="customers",
            description="Customer profile table synchronized from the CRM system.",
            query_language="sql",
            status="active",
            metadata_json="{}",
        )
        session.add(resource)
        session.flush()
        session.add_all(
            [
                ResourceField(
                    datasource_id=datasource.id,
                    resource_id=resource.id,
                    name="id",
                    data_type="integer",
                    nullable=False,
                    ordinal_position=1,
                    description="Stable customer identifier.",
                    status="active",
                    metadata_json="{}",
                ),
                ResourceField(
                    datasource_id=datasource.id,
                    resource_id=resource.id,
                    name="email",
                    data_type="varchar",
                    nullable=True,
                    ordinal_position=2,
                    description="Customer login and notification email.",
                    status="active",
                    metadata_json="{}",
                ),
            ]
        )
        tag = Tag(
            name="pii",
            category="classification",
            description="Personally identifiable information",
        )
        session.add(tag)
        session.flush()
        session.add(ResourceTag(tag_id=tag.id, resource_id=resource.id))
        session.add(
            MaskingPolicy(
                resource_id=resource.id,
                field_name="email",
                strategy="partial",
                config_json='{"prefix":2,"suffix":3,"fill":"*"}',
                status="active",
            )
        )
        AuditService(session).record_event(
            user_id="demo-user",
            api_key_id=api_key.id,
            event_type="metadata_discovery",
            decision="allowed",
            datasource_id=datasource.id,
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
    }


def main() -> None:
    """Parse CLI arguments and print seed credentials as JSON."""

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
