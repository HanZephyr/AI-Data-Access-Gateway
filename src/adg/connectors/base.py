from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

type MetadataColumn = Mapping[str, object]
type RelationSnapshot = Mapping[str, object]
type SchemaSnapshot = Mapping[str, object]
type DatabaseSnapshot = Mapping[str, object]
type MetadataSnapshot = Mapping[str, Sequence[DatabaseSnapshot]]
type QueryRow = Mapping[str, object]
type QueryColumn = Mapping[str, object]


@dataclass(frozen=True)
class QueryResult:
    """Normalized query output returned by all connector implementations."""

    columns: Sequence[QueryColumn]
    rows: Sequence[QueryRow]


class MetadataConnector(Protocol):
    """Connector contract required by metadata scanning and runtime query services."""

    connector_type: str

    def test_connection(self, config: dict[str, object]) -> None:
        """Validate that a datasource config can connect."""
        ...

    def scan_metadata(self, config: dict[str, object]) -> MetadataSnapshot:
        """Return normalized database-first metadata with optional schema nesting."""
        ...

    def execute_query(self, config: dict[str, object], sql: str, limit: int) -> QueryResult:
        """Execute already-authorized SQL."""
        ...
