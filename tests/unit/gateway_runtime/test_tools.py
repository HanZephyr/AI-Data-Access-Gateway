from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.audit.models import AuditEvent
from adg.connectors.base import MetadataConnector, MetadataSnapshot, QueryResult
from adg.connectors.registry import ConnectorRegistry
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.governance import FieldPolicy, ResourcePolicy, ResourceTag, Tag
from adg.control_plane.models.masking import DecryptContext, MaskingPolicy
from adg.control_plane.models.resource import Resource, ResourceField
from adg.gateway_runtime.tools import GatewayRuntimeService
from adg.policy.runtime import IdentityContext


class FakeConnector:
    connector_type = "fake"
    last_sql: str | None = None

    def test_connection(self, config: dict[str, object]) -> None:
        return None

    def scan_metadata(self, config: dict[str, object]) -> MetadataSnapshot:
        return {"databases": []}

    def execute_query(self, config: dict[str, object], sql: str, limit: int) -> QueryResult:
        type(self).last_sql = sql
        if "email" in sql.lower():
            return QueryResult(
                columns=[
                    {"name": "id", "data_type": "integer"},
                    {"name": "email", "data_type": "varchar"},
                ],
                rows=[{"id": 1, "email": "alice@example.com"}],
            )
        return QueryResult(
            columns=[{"name": "id", "data_type": "integer"}],
            rows=[{"id": 1}, {"id": 2}][:limit],
        )


def identity() -> IdentityContext:
    return IdentityContext(user_id="user-1", roles=["analyst"])


def add_datasource(
    db_session: Session,
    *,
    datasource_id: str = "ds_1",
    status: str = "active",
) -> Datasource:
    datasource = Datasource(
        id=datasource_id,
        name=f"Datasource {datasource_id}",
        type="fake",
        datasource_kind="relational",
        config_json="{}",
        status=status,
    )
    db_session.add(datasource)
    return datasource


def add_resource(
    db_session: Session,
    *,
    resource_id: str,
    datasource_id: str = "ds_1",
    path: str = "warehouse.public.customers",
    status: str = "active",
) -> Resource:
    resource = Resource(
        id=resource_id,
        datasource_id=datasource_id,
        parent_id=None,
        kind="relational_table",
        name=path.rsplit(".", 1)[-1],
        path=path,
        display_name=path.rsplit(".", 1)[-1],
        query_language="sql",
        status=status,
        metadata_json="{}",
    )
    db_session.add(resource)
    db_session.flush()
    for index, field_name in enumerate(("id", "email"), start=1):
        db_session.add(
            ResourceField(
                datasource_id=datasource_id,
                resource_id=resource.id,
                name=field_name,
                data_type="integer" if field_name == "id" else "varchar",
                nullable=False,
                ordinal_position=index,
                status="active",
                metadata_json="{}",
            )
        )
    return resource


def runtime(db_session: Session) -> GatewayRuntimeService:
    return GatewayRuntimeService(
        db_session,
        connector_registry=ConnectorRegistry(
            {"fake": cast(type[MetadataConnector], FakeConnector)}
        ),
    )


def allow_resource_read(
    db_session: Session,
    resource_id: str | None = None,
    *,
    subject_type: str = "role",
    subject_id: str = "analyst",
    allow_decrypt: bool = False,
) -> None:
    db_session.add(
        ResourcePolicy(
            subject_type=subject_type,
            subject_id=subject_id,
            effect="allow",
            action="read",
            resource_id=resource_id,
            allow_decrypt=allow_decrypt,
            status="active",
        )
    )


def test_list_datasources_only_returns_datasources_with_visible_resources(
    db_session: Session,
) -> None:
    add_datasource(db_session, datasource_id="ds_visible")
    add_datasource(db_session, datasource_id="ds_hidden")
    add_datasource(db_session, datasource_id="ds_disabled", status="disabled")
    visible = add_resource(
        db_session,
        resource_id="res_visible",
        datasource_id="ds_visible",
        path="warehouse.public.visible_customers",
    )
    hidden = add_resource(
        db_session,
        resource_id="res_hidden",
        datasource_id="ds_hidden",
        path="warehouse.public.hidden_customers",
    )
    allow_resource_read(db_session, visible.id)
    db_session.add(
        ResourcePolicy(
            subject_type="all",
            subject_id="*",
            effect="deny",
            action="read",
            resource_id=hidden.id,
            status="active",
        )
    )

    response = runtime(db_session).list_datasources(identity=identity(), api_key_id="key_1")

    assert [item["id"] for item in response["datasources"]] == ["ds_visible"]


def test_tags_only_include_accessible_resources(db_session: Session) -> None:
    add_datasource(db_session)
    allowed = add_resource(db_session, resource_id="res_allowed")
    denied = add_resource(db_session, resource_id="res_denied", path="warehouse.public.secret")
    public_tag = Tag(id="tag_public", name="public")
    secret_tag = Tag(id="tag_secret", name="secret")
    db_session.add_all([public_tag, secret_tag])
    db_session.add_all(
        [
            ResourceTag(tag_id=public_tag.id, resource_id=allowed.id),
            ResourceTag(tag_id=secret_tag.id, resource_id=denied.id),
            ResourcePolicy(
                subject_type="all",
                subject_id="*",
                effect="allow",
                action="read",
                status="active",
            ),
            ResourcePolicy(
                subject_type="all",
                subject_id="*",
                effect="deny",
                action="read",
                resource_id=denied.id,
                status="active",
            ),
        ]
    )

    response = runtime(db_session).list_tags(identity=identity(), api_key_id="key_1")

    assert response["tags"] == [{"id": "tag_public", "name": "public", "category": None}]


def test_runtime_discovery_hides_disabled_resources_and_fields(
    db_session: Session,
) -> None:
    add_datasource(db_session)
    active = add_resource(db_session, resource_id="res_active")
    disabled = add_resource(
        db_session,
        resource_id="res_disabled",
        path="warehouse.public.secret_customers",
        status="disabled",
    )
    email = db_session.execute(
        select(ResourceField).where(
            ResourceField.resource_id == active.id,
            ResourceField.name == "email",
        )
    ).scalar_one()
    email.status = "disabled"
    db_session.add(
        ResourcePolicy(
            subject_type="all",
            subject_id="*",
            effect="allow",
            action="read",
            status="active",
        )
    )

    listed = runtime(db_session).list_resources(
        identity=identity(),
        api_key_id="key_1",
        datasource_id="ds_1",
    )
    described = runtime(db_session).describe_resource(
        identity=identity(),
        api_key_id="key_1",
        resource_id=active.id,
    )
    disabled_description = runtime(db_session).describe_resource(
        identity=identity(),
        api_key_id="key_1",
        resource_id=disabled.id,
    )

    assert [resource["id"] for resource in listed["resources"]] == [active.id]
    assert [column["name"] for column in described["columns"]] == ["id"]
    assert disabled_description == {"status": "rejected", "reason": "resource_disabled"}


def test_describe_resource_hides_denied_fields(db_session: Session) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")
    allow_resource_read(db_session, resource.id)
    db_session.add(
        FieldPolicy(
            subject_type="all",
            subject_id="*",
            effect="deny",
            resource_id=resource.id,
            field_name="email",
            action="read",
            status="active",
        )
    )

    response = runtime(db_session).describe_resource(
        identity=identity(),
        api_key_id="key_1",
        resource_id=resource.id,
    )

    assert response["columns"] == [
        {
            "name": "id",
            "data_type": "integer",
            "nullable": False,
            "description": None,
            "access": "allowed",
            "masking_strategy": None,
        }
    ]


def test_execute_query_rejects_actual_resources_outside_declared_scope(
    db_session: Session,
) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")
    add_resource(db_session, resource_id="res_orders", path="warehouse.public.orders")
    allow_resource_read(db_session, resource.id)

    response = runtime(db_session).execute_query(
        identity=identity(),
        api_key_id="key_1",
        datasource_id="ds_1",
        resource_ids=["res_customers"],
        query="select id from public.orders",
        limit=100,
    )

    assert response["status"] == "rejected"
    assert response["reason"] == "actual_resource_outside_declared_scope"
    event = db_session.execute(select(AuditEvent)).scalar_one()
    assert event.event_type == "permission_rejected"


def test_execute_query_rejects_unknown_sql_resources(db_session: Session) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")
    allow_resource_read(db_session, resource.id)

    response = runtime(db_session).execute_query(
        identity=identity(),
        api_key_id="key_1",
        datasource_id="ds_1",
        resource_ids=[resource.id],
        query="select id from public.unknown_table",
        limit=100,
    )

    assert response["status"] == "rejected"
    assert response["reason"] == "unknown_sql_resource"
    event = db_session.execute(select(AuditEvent)).scalar_one()
    assert event.event_type == "permission_rejected"


def test_execute_query_runs_allowed_sql_and_audits_success(db_session: Session) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")
    allow_resource_read(db_session, resource.id)

    response = runtime(db_session).execute_query(
        identity=identity(),
        api_key_id="key_1",
        datasource_id="ds_1",
        resource_ids=[resource.id],
        query="select id from public.customers",
        limit=1,
    )

    assert response["status"] == "success"
    assert response["columns"] == [{"name": "id", "data_type": "integer"}]
    assert response["rows"] == [{"id": 1}]
    assert response["query_id"].startswith("qry_")
    assert FakeConnector.last_sql is not None
    assert "LIMIT 1" in FakeConnector.last_sql
    event = db_session.execute(select(AuditEvent)).scalar_one()
    assert event.event_type == "query_execution"
    assert event.decision == "allowed"


def test_execute_query_rejects_denied_field_and_skips_connector(
    db_session: Session,
) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")
    allow_resource_read(db_session, resource.id)
    db_session.add(
        FieldPolicy(
            subject_type="all",
            subject_id="*",
            effect="deny",
            resource_id=resource.id,
            field_name="email",
            action="read",
            status="active",
        )
    )
    FakeConnector.last_sql = None

    response = runtime(db_session).execute_query(
        identity=identity(),
        api_key_id="key_1",
        datasource_id="ds_1",
        resource_ids=[resource.id],
        query="select id, email from public.customers",
        limit=10,
    )

    assert response["status"] == "rejected"
    assert response["reason"] == "field_access_denied:email"
    assert FakeConnector.last_sql is None


def test_execute_query_rejects_disabled_field_and_skips_connector(
    db_session: Session,
) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")
    allow_resource_read(db_session, resource.id)
    db_session.flush()
    email = db_session.execute(
        select(ResourceField).where(
            ResourceField.resource_id == resource.id,
            ResourceField.name == "email",
        )
    ).scalar_one()
    email.status = "disabled"
    FakeConnector.last_sql = None

    response = runtime(db_session).execute_query(
        identity=identity(),
        api_key_id="key_1",
        datasource_id="ds_1",
        resource_ids=[resource.id],
        query="select id, email from public.customers",
        limit=10,
    )

    assert response["status"] == "rejected"
    assert response["reason"] == "field_disabled:email"
    assert FakeConnector.last_sql is None


def test_execute_query_applies_fixed_masking_policy(db_session: Session) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")
    allow_resource_read(db_session, resource.id)
    db_session.add(
        MaskingPolicy(
            resource_id=resource.id,
            field_name="email",
            strategy="fixed",
            config_json='{"replacement":"REDACTED"}',
            status="active",
        )
    )

    response = runtime(db_session).execute_query(
        identity=identity(),
        api_key_id="key_1",
        datasource_id="ds_1",
        resource_ids=[resource.id],
        query="select id, email from public.customers",
        limit=1,
    )

    assert response["rows"] == [{"id": 1, "email": "REDACTED"}]
    assert response["masking"]["masked_columns"] == [
        {"name": "email", "strategy": "fixed"}
    ]


def test_execute_query_applies_reversible_masking_policy(db_session: Session) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")
    allow_resource_read(db_session, resource.id, allow_decrypt=True)
    db_session.add(
        MaskingPolicy(
            resource_id=resource.id,
            field_name="email",
            strategy="reversible",
            config_json="{}",
            status="active",
        )
    )

    response = runtime(db_session).execute_query(
        identity=identity(),
        api_key_id="key_1",
        datasource_id="ds_1",
        resource_ids=[resource.id],
        query="select id, email from public.customers",
        limit=1,
    )

    assert response["rows"][0]["email"].startswith("$adg_rev$")
    assert response["masking"]["masked_columns"] == [
        {"name": "email", "strategy": "reversible"}
    ]
    assert db_session.query(DecryptContext).count() == 1


def test_preview_resource_runs_bounded_preview(db_session: Session) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")
    allow_resource_read(db_session, resource.id)
    db_session.add(
        FieldPolicy(
            subject_type="all",
            subject_id="*",
            effect="deny",
            resource_id=resource.id,
            field_name="email",
            action="read",
            status="active",
        )
    )
    FakeConnector.last_sql = None

    response = runtime(db_session).preview_resource(
        identity=identity(),
        api_key_id="key_1",
        resource_id=resource.id,
        limit=1,
    )

    assert response["status"] == "success"
    assert response["rows"] == [{"id": 1}]
    assert FakeConnector.last_sql == "SELECT id FROM warehouse.public.customers LIMIT 1"


def test_preview_resource_rejects_when_no_fields_are_readable(
    db_session: Session,
) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")
    allow_resource_read(db_session, resource.id)
    db_session.add_all(
        [
            FieldPolicy(
                subject_type="all",
                subject_id="*",
                effect="deny",
                resource_id=resource.id,
                field_name="id",
                action="read",
                status="active",
            ),
            FieldPolicy(
                subject_type="all",
                subject_id="*",
                effect="deny",
                resource_id=resource.id,
                field_name="email",
                action="read",
                status="active",
            ),
        ]
    )
    FakeConnector.last_sql = None

    response = runtime(db_session).preview_resource(
        identity=identity(),
        api_key_id="key_1",
        resource_id=resource.id,
        limit=1,
    )

    assert response == {"status": "rejected", "reason": "no_readable_fields"}
    assert FakeConnector.last_sql is None
