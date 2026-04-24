import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.resource import Resource, ResourceField


class MetadataScanService:
    """Persists connector metadata snapshots into normalized resource tables."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_snapshot(
        self,
        *,
        datasource: Datasource,
        snapshot: Mapping[str, Sequence[Mapping[str, object]]],
    ) -> dict[str, int]:
        """Replace all scanned resources for a datasource in one deterministic pass."""

        existing_resources = {
            resource.path: resource
            for resource in self._session.execute(
                select(Resource).where(Resource.datasource_id == datasource.id)
            ).scalars()
        }
        seen_resource_ids: set[str] = set()
        seen_field_ids: set[str] = set()
        resource_count = 0
        field_count = 0
        scanned_at = datetime.now(UTC)

        # The connector contract is hierarchical: database -> schema -> relation -> column.
        for database_payload in snapshot.get("databases", []):
            database = self._upsert_resource(
                datasource=datasource,
                existing_resources=existing_resources,
                kind="database",
                name=str(database_payload["name"]),
                path=str(database_payload["name"]),
                parent_id=None,
                query_language="sql",
                metadata={},
                scanned_at=scanned_at,
            )
            seen_resource_ids.add(database.id)
            resource_count += 1

            schema_items = database_payload.get("schemas", [])
            if not isinstance(schema_items, Sequence):
                continue

            for schema_payload in schema_items:
                schema_path = f"{database.path}.{schema_payload['name']}"
                schema = self._upsert_resource(
                    datasource=datasource,
                    existing_resources=existing_resources,
                    kind="schema",
                    name=str(schema_payload["name"]),
                    path=schema_path,
                    parent_id=database.id,
                    query_language="sql",
                    metadata={},
                    scanned_at=scanned_at,
                )
                seen_resource_ids.add(schema.id)
                resource_count += 1

                for relation_key, relation_kind in (
                    ("tables", "relational_table"),
                    ("views", "relational_view"),
                ):
                    # Tables and views share the same persistence shape but keep distinct kinds.
                    relation_items = schema_payload.get(relation_key, [])
                    if not isinstance(relation_items, Sequence):
                        continue
                    for relation_payload in relation_items:
                        relation_path = f"{schema.path}.{relation_payload['name']}"
                        relation = self._upsert_resource(
                            datasource=datasource,
                            existing_resources=existing_resources,
                            kind=relation_kind,
                            name=str(relation_payload["name"]),
                            path=relation_path,
                            parent_id=schema.id,
                            query_language="sql",
                            metadata={},
                            scanned_at=scanned_at,
                        )
                        seen_resource_ids.add(relation.id)
                        resource_count += 1

                        column_items = relation_payload.get("columns", [])
                        if not isinstance(column_items, Sequence):
                            continue
                        for index, column_payload in enumerate(column_items, start=1):
                            field = self._upsert_field(
                                datasource=datasource,
                                relation=relation,
                                name=str(column_payload["name"]),
                                data_type=str(column_payload["data_type"]),
                                nullable=bool(column_payload.get("nullable", True)),
                                ordinal_position=int(column_payload.get("ordinal_position", index)),
                                description=(
                                    None
                                    if column_payload.get("description") is None
                                    else str(column_payload["description"])
                                ),
                            )
                            seen_field_ids.add(field.id)
                            field_count += 1

        self._delete_stale_snapshot_rows(datasource.id, seen_resource_ids, seen_field_ids)
        return {"resources": resource_count, "fields": field_count}

    def _upsert_resource(
        self,
        *,
        datasource: Datasource,
        existing_resources: dict[str, Resource],
        kind: str,
        name: str,
        path: str,
        parent_id: str | None,
        query_language: str | None,
        metadata: dict[str, object],
        scanned_at: datetime,
    ) -> Resource:
        """Create or update one resource while preserving operator annotations."""

        resource = existing_resources.get(path)
        if resource is None:
            resource = Resource(
                datasource_id=datasource.id,
                path=path,
                display_name=name,
                description=None,
                status="active",
            )
            self._session.add(resource)
            existing_resources[path] = resource

        resource.parent_id = parent_id
        resource.kind = kind
        resource.name = name
        resource.query_language = query_language
        resource.metadata_json = json.dumps(metadata, separators=(",", ":"))
        resource.scanned_at = scanned_at
        self._session.flush()
        return resource

    def _upsert_field(
        self,
        *,
        datasource: Datasource,
        relation: Resource,
        name: str,
        data_type: str,
        nullable: bool,
        ordinal_position: int,
        description: str | None,
    ) -> ResourceField:
        """Create or update one field while keeping manual descriptions and status."""

        field = self._session.execute(
            select(ResourceField).where(
                ResourceField.datasource_id == datasource.id,
                ResourceField.resource_id == relation.id,
                ResourceField.name == name,
            )
        ).scalar_one_or_none()
        if field is None:
            field = ResourceField(
                datasource_id=datasource.id,
                resource_id=relation.id,
                name=name,
                description=description,
                status="active",
                metadata_json=json.dumps({}, separators=(",", ":")),
            )
            self._session.add(field)
        elif field.description is None and description is not None:
            field.description = description

        field.data_type = data_type
        field.nullable = nullable
        field.ordinal_position = ordinal_position
        field.metadata_json = json.dumps({}, separators=(",", ":"))
        self._session.flush()
        return field

    def _delete_stale_snapshot_rows(
        self,
        datasource_id: str,
        seen_resource_ids: set[str],
        seen_field_ids: set[str],
    ) -> None:
        """Remove assets that disappeared from the latest connector snapshot."""

        field_conditions = [ResourceField.datasource_id == datasource_id]
        if seen_field_ids:
            field_conditions.append(ResourceField.id.not_in(seen_field_ids))
        self._session.execute(delete(ResourceField).where(*field_conditions))

        resource_conditions = [Resource.datasource_id == datasource_id]
        if seen_resource_ids:
            resource_conditions.append(Resource.id.not_in(seen_resource_ids))
        self._session.execute(delete(Resource).where(*resource_conditions))
