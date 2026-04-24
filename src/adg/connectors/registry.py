from adg.connectors.base import MetadataConnector
from adg.connectors.doris.adapter import DorisConnector
from adg.connectors.errors import ConnectorConfigurationError
from adg.connectors.mysql.adapter import MySqlConnector
from adg.connectors.postgres.adapter import PostgresConnector

type ConnectorClass = type[MetadataConnector]


class ConnectorRegistry:
    """Runtime registry that maps connector type strings to connector classes."""

    def __init__(self, connectors: dict[str, ConnectorClass]) -> None:
        self._connectors = dict(connectors)

    def register(self, connector_type: str, connector_class: ConnectorClass) -> None:
        """Add or replace a connector implementation, mainly for tests and plugins."""

        self._connectors[connector_type] = connector_class

    def get(self, connector_type: str) -> ConnectorClass:
        """Return a connector class or raise a domain configuration error."""

        connector_class = self._connectors.get(connector_type)
        if connector_class is None:
            raise ConnectorConfigurationError(
                f"Unsupported connector type: {connector_type}"
            )
        return connector_class

    def create(self, connector_type: str) -> MetadataConnector:
        """Instantiate the connector registered for the requested type."""

        return self.get(connector_type)()


DEFAULT_CONNECTOR_REGISTRY = ConnectorRegistry(
    {
        "postgres": PostgresConnector,
        "mysql": MySqlConnector,
        "doris": DorisConnector,
    }
)


def get_connector_registry() -> ConnectorRegistry:
    """Return the process-wide connector registry used by API and runtime services."""

    return DEFAULT_CONNECTOR_REGISTRY
