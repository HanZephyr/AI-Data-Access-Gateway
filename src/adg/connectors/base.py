from collections.abc import Mapping, Sequence
from typing import Protocol

type MetadataColumn = Mapping[str, object]
type RelationSnapshot = Mapping[str, object]
type SchemaSnapshot = Mapping[str, object]
type DatabaseSnapshot = Mapping[str, object]
type MetadataSnapshot = Mapping[str, Sequence[DatabaseSnapshot]]


class MetadataConnector(Protocol):
    connector_type: str

    def test_connection(self, config: dict[str, object]) -> None: ...

    def scan_metadata(self, config: dict[str, object]) -> MetadataSnapshot: ...
