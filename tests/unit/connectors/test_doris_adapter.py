from pytest import MonkeyPatch

from adg.connectors.doris import adapter
from adg.connectors.doris.adapter import DorisConnector


class FakeResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> "FakeResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self._rows


class FakeConnection:
    def __init__(self) -> None:
        self.statements: list[tuple[str, dict[str, object] | None]] = []

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(
        self,
        statement: object,
        parameters: dict[str, object] | None = None,
    ) -> FakeResult:
        sql = str(statement)
        self.statements.append((sql, parameters))
        if "information_schema.TABLES" in sql:
            return FakeResult(
                [
                    {"table_name": "orders", "table_type": "BASE TABLE"},
                    {"table_name": "daily_sales", "table_type": "VIEW"},
                ]
            )
        if "information_schema.COLUMNS" in sql:
            return FakeResult(
                [
                    {
                        "table_name": "orders",
                        "column_name": "id",
                        "data_type": "largeint",
                        "is_nullable": "NO",
                        "ordinal_position": 1,
                        "column_comment": "primary key",
                    },
                    {
                        "table_name": "orders",
                        "column_name": "created_at",
                        "data_type": "datetimev2",
                        "is_nullable": "YES",
                        "ordinal_position": 2,
                        "column_comment": None,
                    },
                    {
                        "table_name": "daily_sales",
                        "column_name": "total",
                        "data_type": "decimal",
                        "is_nullable": "YES",
                        "ordinal_position": 1,
                        "column_comment": "daily total",
                    },
                ]
            )
        raise AssertionError(f"unexpected SQL: {sql}")


class FakeEngine:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def connect(self) -> FakeConnection:
        return self.connection


def test_doris_scan_metadata_uses_raw_information_schema(monkeypatch: MonkeyPatch) -> None:
    connection = FakeConnection()

    def fake_create_engine(url: object) -> FakeEngine:
        return FakeEngine(connection)

    monkeypatch.setattr(adapter, "create_engine", fake_create_engine, raising=False)
    monkeypatch.setattr(DorisConnector, "_require_dependency", lambda self: None)

    snapshot = DorisConnector().scan_metadata({"database": "warehouse"})

    assert snapshot == {
        "databases": [
            {
                "name": "warehouse",
                "schemas": [
                    {
                        "name": "warehouse",
                        "tables": [
                            {
                                "name": "orders",
                                "kind": "table",
                                "schema": "warehouse",
                                "columns": [
                                    {
                                        "name": "id",
                                        "data_type": "largeint",
                                        "nullable": False,
                                        "ordinal_position": 1,
                                        "description": "primary key",
                                    },
                                    {
                                        "name": "created_at",
                                        "data_type": "datetimev2",
                                        "nullable": True,
                                        "ordinal_position": 2,
                                        "description": None,
                                    },
                                ],
                            }
                        ],
                        "views": [
                            {
                                "name": "daily_sales",
                                "kind": "view",
                                "schema": "warehouse",
                                "columns": [
                                    {
                                        "name": "total",
                                        "data_type": "decimal",
                                        "nullable": True,
                                        "ordinal_position": 1,
                                        "description": "daily total",
                                    },
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }
    assert all(parameters == {"schema": "warehouse"} for _, parameters in connection.statements)
