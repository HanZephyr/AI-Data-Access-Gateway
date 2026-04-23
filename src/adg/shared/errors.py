class AdgError(Exception):
    """Base class for domain errors."""


class NotFoundError(AdgError):
    """Raised when a requested entity does not exist."""


class ValidationError(AdgError):
    """Raised when operator input violates gateway rules."""
