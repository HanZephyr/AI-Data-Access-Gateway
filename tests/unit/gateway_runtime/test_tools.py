from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.audit.models import AuditEvent
from adg.connectors.base import MetadataConnector, MetadataSnapshot, QueryResult
from adg.connectors.registry import ConnectorRegistry
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.governance import FieldPolicy, ResourcePolicy, ResourceTag, Tag
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
        return QueryResult(
            columns=[{"name": "id", "data_type": "integer"}],
            rows=[{"id": 1}, {"id": 2}][:limit],
        )


def identity() -> IdentityContext:
    return IdentityContext(tenant_id="tenant-a", user_id="user-1", roles=["analyst"])


def add_datasource(
    db_session: Session,
    *,
    datasource_id: str = "ds_1",
    status: str = "active",
) -> Datasource:
    datasource = Datasource(
        id=datasource_id,
        tenant_id="tenant-a",
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
) -> Resource:
    resource = Resource(
        id=resource_id,
        tenant_id="tenant-a",
        datasource_id=datasource_id,
        parent_id=None,
        kind="relational_table",
        name=path.rsplit(".", 1)[-1],
        path=path,
        display_name=path.rsplit(".", 1)[-1],
        query_language="sql",
        metadata_json="{}",
    )
    db_session.add(resource)
    db_session.flush()
    for index, field_name in enumerate(("id", "email"), start=1):
        db_session.add(
            ResourceField(
                tenant_id="tenant-a",
                datasource_id=datasource_id,
                resource_id=resource.id,
                name=field_name,
                data_type="integer" if field_name == "id" else "varchar",
                nullable=False,
                ordinal_position=index,
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


def test_list_datasources_is_tenant_scoped_and_active_only(db_session: Session) -> None:
    add_datasource(db_session, datasource_id="ds_active")
    add_datasource(db_session, datasource_id="ds_disabled", status="disabled")
    db_session.add(
        Datasource(
            id="ds_other",
            tenant_id="tenant-b",
            name="Other",
            type="fake",
            datasource_kind="relational",
            config_json="{}",
            status="active",
        )
    )

    response = runtime(db_session).list_datasources(identity=identity(), api_key_id="key_1")

    assert [item["id"] for item in response["datasources"]] == ["ds_active"]


def test_tags_only_include_accessible_resources(db_session: Session) -> None:
    add_datasource(db_session)
    allowed = add_resource(db_session, resource_id="res_allowed")
    denied = add_resource(db_session, resource_id="res_denied", path="warehouse.public.secret")
    public_tag = Tag(id="tag_public", tenant_id="tenant-a", name="public")
    secret_tag = Tag(id="tag_secret", tenant_id="tenant-a", name="secret")
    db_session.add_all([public_tag, secret_tag])
    db_session.add_all(
        [
            ResourceTag(tenant_id="tenant-a", tag_id=public_tag.id, resource_id=allowed.id),
            ResourceTag(tenant_id="tenant-a", tag_id=secret_tag.id, resource_id=denied.id),
            ResourcePolicy(
                tenant_id="tenant-a",
                subject_type="all",
                subject_id="*",
                effect="allow",
                action="read",
                status="active",
            ),
            ResourcePolicy(
                tenant_id="tenant-a",
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


def test_describe_resource_marks_denied_fields(db_session: Session) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")
    db_session.add(
        FieldPolicy(
            tenant_id="tenant-a",
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

    fields_by_name = {field["name"]: field for field in response["columns"]}
    assert fields_by_name["id"]["access"] == "allowed"
    assert fields_by_name["email"]["access"] == "denied"


def test_execute_query_rejects_actual_resources_outside_declared_scope(
    db_session: Session,
) -> None:
    add_datasource(db_session)
    add_resource(db_session, resource_id="res_customers")
    add_resource(db_session, resource_id="res_orders", path="warehouse.public.orders")

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


def test_execute_query_runs_allowed_sql_and_audits_success(db_session: Session) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")

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


def test_preview_resource_runs_bounded_preview(db_session: Session) -> None:
    add_datasource(db_session)
    resource = add_resource(db_session, resource_id="res_customers")

    response = runtime(db_session).preview_resource(
        identity=identity(),
        api_key_id="key_1",
        resource_id=resource.id,
        limit=1,
    )

    assert response["status"] == "success"
    assert response["rows"] == [{"id": 1}]
