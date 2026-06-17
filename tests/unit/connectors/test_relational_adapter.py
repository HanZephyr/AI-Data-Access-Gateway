from typing import Any, cast

from pytest import MonkeyPatch

from adg.connectors import relational
from adg.connectors.relational import RelationalConnector


class FakeScalarResult:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def all(self) -> list[str]:
        return self._values


class FakeResult:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._values)


class FakeDialect:
    name = "postgresql"


class FakeConnection:
    dialect = FakeDialect()

    def __init__(self, database: str | None) -> None:
        self.database = database

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def exec_driver_sql(self, sql: str) -> FakeResult:
        assert "pg_database" in sql
        return FakeResult(["analytics", "warehouse"])


class FakeEngine:
    def __init__(self, database: str | None) -> None:
        self.database = database

    def connect(self) -> FakeConnection:
        return FakeConnection(self.database)


class FakeInspector:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def get_schema_names(self) -> list[str]:
        return ["public"]

    def get_table_names(self, schema: str | None = None) -> list[str]:
        assert schema == "public"
        return [f"{self.connection.database}_orders"]

    def get_view_names(self, schema: str | None = None) -> list[str]:
        assert schema == "public"
        return []

    def get_columns(self, table_name: str, schema: str | None = None) -> list[dict[str, object]]:
        assert schema == "public"
        assert table_name.endswith("_orders")
        return [{"name": "id", "type": "integer", "nullable": False}]


class FakePostgresConnector(RelationalConnector):
    connector_type = "fake-postgres"
    sqlalchemy_drivername = "postgresql+psycopg"
    dependency_name = "psycopg"
    install_extra = "postgres"


class FakeDmlResult:
    returns_rows = False
    rowcount = 3


class FakeDmlConnection:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def __enter__(self) -> "FakeDmlConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object) -> FakeDmlResult:
        self.statements.append(str(statement))
        return FakeDmlResult()


class FakeDmlEngine:
    def __init__(self) -> None:
        self.connection = FakeDmlConnection()

    def begin(self) -> FakeDmlConnection:
        return self.connection


def test_relational_scan_metadata_discovers_all_accessible_databases_when_database_is_blank(
    monkeypatch: MonkeyPatch,
) -> None:
    created_databases: list[str | None] = []

    def fake_create_engine(url: object) -> FakeEngine:
        database = getattr(url, "database", None)
        created_databases.append(database)
        return FakeEngine(database)

    def fake_inspect(connection: FakeConnection) -> FakeInspector:
        return FakeInspector(connection)

    monkeypatch.setattr(relational, "create_engine", fake_create_engine)
    monkeypatch.setattr(relational, "inspect", fake_inspect)
    monkeypatch.setattr(FakePostgresConnector, "_require_dependency", lambda self: None)

    snapshot = FakePostgresConnector().scan_metadata({"host": "db.internal"})
    databases = cast(list[dict[str, Any]], snapshot["databases"])
    schemas = cast(list[dict[str, Any]], databases[0]["schemas"])
    tables = cast(list[dict[str, Any]], schemas[0]["tables"])

    assert created_databases == [None, "analytics", "warehouse"]
    assert [database["name"] for database in databases] == ["analytics", "warehouse"]
    assert tables[0]["name"] == "analytics_orders"


def test_relational_execute_query_returns_affected_rows_for_non_row_statements(
    monkeypatch: MonkeyPatch,
) -> None:
    fake_engine = FakeDmlEngine()

    monkeypatch.setattr(relational, "create_engine", lambda url: fake_engine)
    monkeypatch.setattr(FakePostgresConnector, "_require_dependency", lambda self: None)

    result = FakePostgresConnector().execute_query(
        {"host": "db.internal"},
        "update public.customers set name = 'Alice' where id = 1",
        100,
    )

    assert fake_engine.connection.statements == [
        "update public.customers set name = 'Alice' where id = 1"
    ]
    assert result.columns == [{"name": "affected_rows", "data_type": "integer"}]
    assert result.rows == [{"affected_rows": 3}]
