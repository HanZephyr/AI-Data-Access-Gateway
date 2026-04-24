from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.audit.service import AuditService
from adg.connectors.registry import ConnectorRegistry, get_connector_registry
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.governance import ResourceTag, Tag
from adg.control_plane.models.resource import Resource, ResourceField
from adg.policy.runtime import IdentityContext, RuntimePolicyService
from adg.shared.errors import NotFoundError
from adg.sql_guard.guard import SqlGuard


class GatewayRuntimeService:
    def __init__(
        self,
        session: Session,
        *,
        connector_registry: ConnectorRegistry | None = None,
    ) -> None:
        self._session = session
        self._connector_registry = connector_registry or get_connector_registry()
        self._policy = RuntimePolicyService(session)
        self._audit = AuditService(session)

    def list_datasources(
        self,
        *,
        identity: IdentityContext,
        api_key_id: str,
    ) -> dict[str, Any]:
        self._session.flush()
        datasources = self._session.execute(
            select(Datasource).where(
                Datasource.tenant_id == identity.tenant_id,
                Datasource.status == "active",
            )
        ).scalars()
        response = {
            "datasources": [
                {
                    "id": datasource.id,
                    "name": datasource.name,
                    "type": datasource.type,
                    "datasource_kind": datasource.datasource_kind,
                }
                for datasource in datasources
            ]
        }
        self._record_discovery(identity, api_key_id, "list_datasources", None, [])
        return response

    def list_tags(self, *, identity: IdentityContext, api_key_id: str) -> dict[str, Any]:
        self._session.flush()
        visible_resource_ids = {
            resource.id for resource in self._visible_resources(identity=identity)
        }
        tags = self._session.execute(
            select(Tag)
            .join(ResourceTag, ResourceTag.tag_id == Tag.id)
            .where(
                Tag.tenant_id == identity.tenant_id,
                ResourceTag.resource_id.in_(visible_resource_ids),
            )
            .order_by(Tag.name)
        ).scalars()
        response = {
            "tags": [
                {"id": tag.id, "name": tag.name, "category": tag.category}
                for tag in self._unique_tags(tags)
            ]
        }
        self._record_discovery(identity, api_key_id, "list_tags", None, [])
        return response

    def list_resources(
        self,
        *,
        identity: IdentityContext,
        api_key_id: str,
        datasource_id: str,
    ) -> dict[str, Any]:
        self._session.flush()
        resources = [
            resource
            for resource in self._visible_resources(identity=identity, datasource_id=datasource_id)
        ]
        self._record_discovery(identity, api_key_id, "list_resources", datasource_id, [])
        return {"resources": [self._serialize_resource(resource) for resource in resources]}

    def list_resources_by_tag(
        self,
        *,
        identity: IdentityContext,
        api_key_id: str,
        tag_names: list[str],
    ) -> dict[str, Any]:
        self._session.flush()
        tag_rows = self._session.execute(
            select(Tag).where(Tag.tenant_id == identity.tenant_id, Tag.name.in_(tag_names))
        ).scalars()
        tag_ids = [tag.id for tag in tag_rows]
        resources = [
            resource
            for resource in self._visible_resources(identity=identity)
            if self._resource_has_any_tag(resource, tag_ids)
        ]
        self._record_discovery(identity, api_key_id, "list_resources_by_tag", None, [])
        return {"resources": [self._serialize_resource(resource) for resource in resources]}

    def describe_resource(
        self,
        *,
        identity: IdentityContext,
        api_key_id: str,
        resource_id: str,
    ) -> dict[str, Any]:
        self._session.flush()
        resource = self._get_resource(resource_id)
        access = self._policy.check_resource_access(
            identity=identity,
            resource=resource,
            action="read",
        )
        if not access.allowed:
            self._record_rejection(
                identity,
                api_key_id,
                "permission_rejected",
                resource.datasource_id,
                [resource.id],
                None,
                access.reason,
            )
            return {"status": "rejected", "reason": access.reason}

        fields = self._session.execute(
            select(ResourceField)
            .where(ResourceField.resource_id == resource.id)
            .order_by(ResourceField.ordinal_position)
        ).scalars()
        columns = []
        for field in fields:
            field_access = self._policy.check_field_access(
                identity=identity,
                resource=resource,
                field_name=field.name,
                action="read",
            )
            columns.append(
                {
                    "name": field.name,
                    "data_type": field.data_type,
                    "nullable": field.nullable,
                    "access": "allowed" if field_access.allowed else "denied",
                    "masking_strategy": None,
                }
            )
        self._record_discovery(
            identity, api_key_id, "describe_resource", resource.datasource_id, [resource.id]
        )
        return {
            "id": resource.id,
            "name": resource.name,
            "path": resource.path,
            "kind": resource.kind,
            "columns": columns,
        }

    def preview_resource(
        self,
        *,
        identity: IdentityContext,
        api_key_id: str,
        resource_id: str,
        limit: int,
    ) -> dict[str, Any]:
        self._session.flush()
        resource = self._get_resource(resource_id)
        return self.execute_query(
            identity=identity,
            api_key_id=api_key_id,
            datasource_id=resource.datasource_id,
            resource_ids=[resource.id],
            query=f"select * from {resource.path}",
            limit=limit,
            event_type="resource_preview",
        )

    def execute_query(
        self,
        *,
        identity: IdentityContext,
        api_key_id: str,
        datasource_id: str,
        resource_ids: list[str],
        query: str,
        limit: int,
        event_type: str = "query_execution",
    ) -> dict[str, Any]:
        self._session.flush()
        datasource = self._get_datasource(datasource_id)
        declared_resources = [self._get_resource(resource_id) for resource_id in resource_ids]
        for resource in declared_resources:
            decision = self._policy.check_resource_access(
                identity=identity,
                resource=resource,
                action="read",
            )
            if not decision.allowed:
                self._record_rejection(
                    identity,
                    api_key_id,
                    "permission_rejected",
                    datasource_id,
                    resource_ids,
                    query,
                    decision.reason,
                )
                return {"status": "rejected", "reason": decision.reason}

        guard_result = SqlGuard(default_limit=limit, max_limit=limit).check(query)
        if not guard_result.allowed or guard_result.normalized_sql is None:
            reason = ",".join(guard_result.rejection_reasons)
            self._record_rejection(
                identity,
                api_key_id,
                "sql_rejected",
                datasource_id,
                resource_ids,
                query,
                reason,
            )
            return {"status": "rejected", "reason": reason}

        actual_resources = self._resolve_guard_resources(
            identity=identity,
            datasource_id=datasource_id,
            resource_paths=guard_result.accessed_resources,
        )
        declared_ids = set(resource_ids)
        actual_ids = {resource.id for resource in actual_resources}
        if not actual_ids.issubset(declared_ids):
            reason = "actual_resource_outside_declared_scope"
            self._record_rejection(
                identity,
                api_key_id,
                "permission_rejected",
                datasource_id,
                resource_ids,
                query,
                reason,
            )
            return {"status": "rejected", "reason": reason}

        connector = self._connector_registry.create(datasource.type)
        result = connector.execute_query(datasource.config(), guard_result.normalized_sql, limit)
        query_id = f"qry_{uuid4()}"
        self._audit.record_event(
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            api_key_id=api_key_id,
            event_type=event_type,
            decision="allowed",
            datasource_id=datasource_id,
            resource_ids=sorted(actual_ids),
            query_id=query_id,
            sql_text=guard_result.normalized_sql,
            reason=None,
            metadata={
                "warnings": guard_result.warnings,
                "accessed_fields": guard_result.accessed_fields,
            },
        )
        self._session.flush()
        return {
            "query_id": query_id,
            "status": "success",
            "columns": list(result.columns),
            "rows": list(result.rows),
            "masking": {"masked_columns": []},
            "warnings": guard_result.warnings,
        }

    def _visible_resources(
        self,
        *,
        identity: IdentityContext,
        datasource_id: str | None = None,
    ) -> list[Resource]:
        conditions = [
            Resource.tenant_id == identity.tenant_id,
            Resource.kind.in_(["relational_table", "relational_view"]),
        ]
        if datasource_id is not None:
            conditions.append(Resource.datasource_id == datasource_id)
        resources = self._session.execute(select(Resource).where(*conditions)).scalars()
        return [
            resource
            for resource in resources
            if self._policy.check_resource_access(
                identity=identity,
                resource=resource,
                action="read",
            ).allowed
        ]

    def _resolve_guard_resources(
        self,
        *,
        identity: IdentityContext,
        datasource_id: str,
        resource_paths: list[str],
    ) -> list[Resource]:
        resources = list(
            self._session.execute(
                select(Resource).where(
                    Resource.tenant_id == identity.tenant_id,
                    Resource.datasource_id == datasource_id,
                    Resource.kind.in_(["relational_table", "relational_view"]),
                )
            ).scalars()
        )
        matched: list[Resource] = []
        for resource_path in resource_paths:
            matches = [
                resource
                for resource in resources
                if resource.path == resource_path or resource.path.endswith(f".{resource_path}")
            ]
            if len(matches) == 1:
                matched.append(matches[0])
        return matched

    def _get_datasource(self, datasource_id: str) -> Datasource:
        datasource = self._session.get(Datasource, datasource_id)
        if datasource is None:
            raise NotFoundError("Datasource not found")
        return datasource

    def _get_resource(self, resource_id: str) -> Resource:
        resource = self._session.get(Resource, resource_id)
        if resource is None:
            raise NotFoundError("Resource not found")
        return resource

    def _resource_has_any_tag(self, resource: Resource, tag_ids: list[str]) -> bool:
        if not tag_ids:
            return False
        return (
            self._session.execute(
                select(ResourceTag).where(
                    ResourceTag.tenant_id == resource.tenant_id,
                    ResourceTag.resource_id == resource.id,
                    ResourceTag.tag_id.in_(tag_ids),
                )
            ).scalar_one_or_none()
            is not None
        )

    def _unique_tags(self, tags: Any) -> list[Tag]:
        seen: set[str] = set()
        unique: list[Tag] = []
        for tag in tags:
            if tag.id not in seen:
                seen.add(tag.id)
                unique.append(tag)
        return unique

    def _serialize_resource(self, resource: Resource) -> dict[str, Any]:
        return {
            "id": resource.id,
            "datasource_id": resource.datasource_id,
            "kind": resource.kind,
            "name": resource.name,
            "path": resource.path,
            "display_name": resource.display_name,
            "query_language": resource.query_language,
        }

    def _record_discovery(
        self,
        identity: IdentityContext,
        api_key_id: str,
        tool_name: str,
        datasource_id: str | None,
        resource_ids: list[str],
    ) -> None:
        self._audit.record_event(
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            api_key_id=api_key_id,
            event_type="metadata_discovery",
            decision="allowed",
            datasource_id=datasource_id,
            resource_ids=resource_ids,
            query_id=None,
            sql_text=None,
            reason=None,
            metadata={"tool": tool_name},
        )
        self._session.flush()

    def _record_rejection(
        self,
        identity: IdentityContext,
        api_key_id: str,
        event_type: str,
        datasource_id: str | None,
        resource_ids: list[str],
        sql_text: str | None,
        reason: str,
    ) -> None:
        self._audit.record_event(
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            api_key_id=api_key_id,
            event_type=event_type,
            decision="denied",
            datasource_id=datasource_id,
            resource_ids=resource_ids,
            query_id=None,
            sql_text=sql_text,
            reason=reason,
            metadata={},
        )
        self._session.flush()
