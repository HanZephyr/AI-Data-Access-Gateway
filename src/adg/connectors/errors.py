from adg.shared.errors import AdgError


class ConnectorConfigurationError(AdgError):
    """Raised when a datasource connector type is unsupported."""


class ConnectorDependencyError(AdgError):
    """Raised when an optional datasource driver is unavailable."""


class ConnectorOperationError(AdgError):
    """Raised when connector execution fails."""
