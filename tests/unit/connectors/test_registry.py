from adg.connectors.doris.adapter import DorisConnector
from adg.connectors.errors import ConnectorConfigurationError
from adg.connectors.mysql.adapter import MySqlConnector
from adg.connectors.postgres.adapter import PostgresConnector
from adg.connectors.registry import ConnectorRegistry, get_connector_registry


def test_default_registry_resolves_supported_connectors() -> None:
    registry = get_connector_registry()

    assert registry.get("postgres") is PostgresConnector
    assert registry.get("mysql") is MySqlConnector
    assert registry.get("doris") is DorisConnector


def test_registry_rejects_unsupported_connector_type() -> None:
    registry = ConnectorRegistry({})

    try:
        registry.get("sqlite")
    except ConnectorConfigurationError as error:
        assert str(error) == "Unsupported connector type: sqlite"
    else:
        raise AssertionError("expected ConnectorConfigurationError")
