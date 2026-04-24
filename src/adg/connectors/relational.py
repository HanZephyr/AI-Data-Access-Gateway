import importlib
from collections.abc import Sequence

from sqlalchemy import URL, create_engine, inspect, text

from adg.connectors.base import MetadataColumn, MetadataSnapshot, QueryResult
from adg.connectors.errors import ConnectorDependencyError, ConnectorOperationError


class RelationalConnector:
    """Base implementation for SQLAlchemy-backed relational metadata connectors."""

    connector_type = ""
    sqlalchemy_drivername = ""
    dependency_name = ""
    install_extra = ""

    def _require_dependency(self) -> None:
        """Fail early with an install hint when an optional DB driver is missing."""

        try:
            importlib.import_module(self.dependency_name)
        except ModuleNotFoundError as error:
            raise ConnectorDependencyError(
                f"Connector '{self.connector_type}' requires optional extra '{self.install_extra}'"
            ) from error

    def _build_url(self, config: dict[str, object]) -> URL:
        """Translate persisted datasource config into a SQLAlchemy URL."""

        port_value = config.get("port")
        return URL.create(
            drivername=self.sqlalchemy_drivername,
            username=str(config.get("username", "")) or None,
            password=str(config.get("password", "")) or None,
            host=str(config.get("host", "")) or None,
            port=int(str(port_value)) if port_value is not None else None,
            database=str(config.get("database", "")) or None,
        )

    def test_connection(self, config: dict[str, object]) -> None:
        """Open a connection and run a minimal query to validate connectivity."""

        self._require_dependency()
        try:
            engine = create_engine(self._build_url(config))
            with engine.connect() as connection:
                connection.exec_driver_sql("select 1")
        except ConnectorDependencyError:
            raise
        except Exception as error:
            raise ConnectorOperationError(str(error)) from error

    def scan_metadata(self, config: dict[str, object]) -> MetadataSnapshot:
        """Inspect schemas, tables, views, and columns into the shared snapshot shape."""

        self._require_dependency()
        try:
            engine = create_engine(self._build_url(config))
            with engine.connect() as connection:
                inspector = inspect(connection)
                database_name = str(config.get("database", "default"))
                schemas: list[dict[str, object]] = []
                for schema_name in inspector.get_schema_names():
                    # SQLAlchemy inspectors expose tables and views separately; ADG preserves both.
                    tables = [
                        self._build_relation_payload(
                            relation_name=table_name,
                            relation_kind="table",
                            schema_name=schema_name,
                            columns=inspector.get_columns(table_name, schema=schema_name),
                        )
                        for table_name in inspector.get_table_names(schema=schema_name)
                    ]
                    views = [
                        self._build_relation_payload(
                            relation_name=view_name,
                            relation_kind="view",
                            schema_name=schema_name,
                            columns=inspector.get_columns(view_name, schema=schema_name),
                        )
                        for view_name in inspector.get_view_names(schema=schema_name)
                    ]
                    schemas.append(
                        {
                            "name": schema_name,
                            "tables": tables,
                            "views": views,
                        }
                    )
        except ConnectorDependencyError:
            raise
        except Exception as error:
            raise ConnectorOperationError(str(error)) from error

        return {"databases": [{"name": database_name, "schemas": schemas}]}

    def execute_query(self, config: dict[str, object], sql: str, limit: int) -> QueryResult:
        """Execute already-approved read-only SQL and return normalized rows."""

        self._require_dependency()
        try:
            engine = create_engine(self._build_url(config))
            with engine.connect() as connection:
                result = connection.execute(text(sql))
                rows = [dict(row) for row in result.mappings().fetchmany(limit)]
                columns = [{"name": str(name), "data_type": "unknown"} for name in result.keys()]
        except ConnectorDependencyError:
            raise
        except Exception as error:
            raise ConnectorOperationError(str(error)) from error

        return QueryResult(columns=columns, rows=rows)

    def _build_relation_payload(
        self,
        *,
        relation_name: str,
        relation_kind: str,
        schema_name: str,
        columns: Sequence[MetadataColumn],
    ) -> dict[str, object]:
        """Normalize one table or view and its columns for snapshot persistence."""

        return {
            "name": relation_name,
            "kind": relation_kind,
            "schema": schema_name,
            "columns": [
                {
                    "name": str(column["name"]),
                    "data_type": str(column["type"]),
                    "nullable": bool(column.get("nullable", True)),
                    "ordinal_position": index,
                    "description": None,
                }
                for index, column in enumerate(columns, start=1)
            ],
        }
