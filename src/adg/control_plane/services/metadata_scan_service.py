import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from sqlalchemy import delete
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

        # Snapshot replacement deliberately deletes fields first because they reference resources.
        self._session.execute(
            delete(ResourceField).where(ResourceField.datasource_id == datasource.id)
        )
        self._session.execute(delete(Resource).where(Resource.datasource_id == datasource.id))

        resource_ids_by_path: dict[str, str] = {}
        resource_count = 0
        field_count = 0
        scanned_at = datetime.now(UTC)

        # The connector contract is hierarchical: database -> schema -> relation -> column.
        for database_payload in snapshot.get("databases", []):
            database = self._create_resource(
                datasource=datasource,
                kind="database",
                name=str(database_payload["name"]),
                path=str(database_payload["name"]),
                parent_id=None,
                query_language="sql",
                metadata={},
                scanned_at=scanned_at,
            )
            resource_ids_by_path[database.path] = database.id
            resource_count += 1

            schema_items = database_payload.get("schemas", [])
            if not isinstance(schema_items, Sequence):
                continue

            for schema_payload in schema_items:
                schema_path = f"{database.path}.{schema_payload['name']}"
                schema = self._create_resource(
                    datasource=datasource,
                    kind="schema",
                    name=str(schema_payload["name"]),
                    path=schema_path,
                    parent_id=database.id,
                    query_language="sql",
                    metadata={},
                    scanned_at=scanned_at,
                )
                resource_ids_by_path[schema.path] = schema.id
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
                        relation = self._create_resource(
                            datasource=datasource,
                            kind=relation_kind,
                            name=str(relation_payload["name"]),
                            path=relation_path,
                            parent_id=schema.id,
                            query_language="sql",
                            metadata={},
                            scanned_at=scanned_at,
                        )
                        resource_count += 1

                        column_items = relation_payload.get("columns", [])
                        if not isinstance(column_items, Sequence):
                            continue
                        for index, column_payload in enumerate(column_items, start=1):
                            field = ResourceField(
                                datasource_id=datasource.id,
                                resource_id=relation.id,
                                name=str(column_payload["name"]),
                                data_type=str(column_payload["data_type"]),
                                nullable=bool(column_payload.get("nullable", True)),
                                ordinal_position=int(
                                    column_payload.get("ordinal_position", index)
                                ),
                                description=(
                                    None
                                    if column_payload.get("description") is None
                                    else str(column_payload["description"])
                                ),
                                metadata_json=json.dumps({}, separators=(",", ":")),
                            )
                            self._session.add(field)
                            field_count += 1

        return {"resources": resource_count, "fields": field_count}

    def _create_resource(
        self,
        *,
        datasource: Datasource,
        kind: str,
        name: str,
        path: str,
        parent_id: str | None,
        query_language: str | None,
        metadata: dict[str, object],
        scanned_at: datetime,
    ) -> Resource:
        """Create one resource row and flush so child rows can reference its id."""

        resource = Resource(
            datasource_id=datasource.id,
            parent_id=parent_id,
            kind=kind,
            name=name,
            path=path,
            display_name=name,
            query_language=query_language,
            metadata_json=json.dumps(metadata, separators=(",", ":")),
            scanned_at=scanned_at,
        )
        self._session.add(resource)
        self._session.flush()
        return resource
