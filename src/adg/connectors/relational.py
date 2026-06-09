import importlib
from collections.abc import Sequence

from sqlalchemy import URL, create_engine, inspect, text
from sqlalchemy.engine import Connection

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
        configured_database = str(config.get("database", "")).strip()
        try:
            if configured_database:
                engine = create_engine(self._build_url(config))
                with engine.connect() as connection:
                    databases = [self._scan_database(connection, configured_database)]
            else:
                discovery_engine = create_engine(self._build_url(config))
                with discovery_engine.connect() as connection:
                    database_names = self._discover_database_names(connection)
                databases = []
                for database_name in database_names:
                    database_config = {**config, "database": database_name}
                    database_engine = create_engine(self._build_url(database_config))
                    with database_engine.connect() as connection:
                        databases.append(self._scan_database(connection, database_name))
        except ConnectorDependencyError:
            raise
        except Exception as error:
            raise ConnectorOperationError(str(error)) from error

        return {"databases": databases}

    def _discover_database_names(self, connection: Connection) -> list[str]:
        """Return accessible logical databases when the datasource did not pin one."""

        dialect_name = str(getattr(connection.dialect, "name", "")).lower()
        if dialect_name.startswith("postgres"):
            result = connection.exec_driver_sql(
                """
                SELECT datname
                FROM pg_database
                WHERE datallowconn = true
                  AND datistemplate = false
                ORDER BY datname
                """
            )
            return [str(name) for name in result.scalars().all() if str(name).strip()]
        if dialect_name in {"mysql", "mariadb"}:
            result = connection.exec_driver_sql("SHOW DATABASES")
            system_databases = {"information_schema", "mysql", "performance_schema", "sys"}
            return [
                str(name)
                for name in result.scalars().all()
                if str(name).strip() and str(name).lower() not in system_databases
            ]
        fallback_name = self._connection_database_name(connection)
        return [fallback_name] if fallback_name else ["default"]

    def _connection_database_name(self, connection: Connection) -> str | None:
        """Best-effort database name fallback for dialects without discovery support."""

        direct_name = getattr(connection, "database", None)
        if direct_name:
            return str(direct_name)
        engine = getattr(connection, "engine", None)
        url = getattr(engine, "url", None)
        database_name = getattr(url, "database", None)
        return str(database_name) if database_name else None

    def _scan_database(self, connection: Connection, database_name: str) -> dict[str, object]:
        """Inspect one connected database into ADG's database-first snapshot shape."""

        inspector = inspect(connection)
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
        return {"name": database_name, "schemas": schemas}

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
