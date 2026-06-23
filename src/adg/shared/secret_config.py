from typing import Final, Literal, Required, TypedDict, TypeGuard

from cryptography.fernet import Fernet

from adg.app.settings import get_settings
from adg.shared.crypto import (
    FERNET_ENVELOPE_KIND,
    decrypt_fernet_envelope,
    derive_legacy_fernet_key,
    encrypt_fernet_envelope,
)

SECRET_ENVELOPE_KIND: Final[str] = FERNET_ENVELOPE_KIND
SECRET_PLACEHOLDER_KIND: Final[str] = "secret_placeholder"
SECRET_FIELD_NAMES: Final[frozenset[str]] = frozenset({"password"})
_OMIT = object()


class EncryptedSecret(TypedDict, total=False):
    kind: Required[Literal["encrypted_secret"]]
    ciphertext: Required[str]
    version: int
    kdf: str
    salt: str
    iterations: int


class SecretPlaceholder(TypedDict):
    kind: Literal["secret_placeholder"]
    configured: bool


class SecretConfigService:
    """Protects persisted datasource secrets and reveals them only for runtime use."""

    def __init__(self, *, credential_encryption_key: str, kdf_iterations: int = 390_000) -> None:
        self._credential_encryption_key = credential_encryption_key
        self._kdf_iterations = kdf_iterations

    @classmethod
    def from_settings(cls) -> "SecretConfigService":
        """Build the service from the process-wide application settings."""

        settings = get_settings()
        return cls(
            credential_encryption_key=settings.credential_encryption_key,
            kdf_iterations=settings.secret_kdf_iterations,
        )

    def protect_persisted_config(
        self,
        config: dict[str, object],
        *,
        previous: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Encrypt secret replacements and preserve prior values when updates omit them."""

        previous_config = previous or {}
        protected: dict[str, object] = {}

        for raw_key, value in config.items():
            key = str(raw_key)
            if key in SECRET_FIELD_NAMES:
                protected_value = self._protect_secret_value(
                    value,
                    previous=previous_config.get(key),
                )
                if protected_value is not _OMIT:
                    protected[key] = protected_value
                continue
            protected[key] = value

        for secret_field in SECRET_FIELD_NAMES:
            if secret_field in protected or secret_field in config:
                continue
            previous_value = previous_config.get(secret_field, _OMIT)
            if previous_value is not _OMIT:
                reused = self._reuse_previous_secret(previous_value)
                if reused is not _OMIT:
                    protected[secret_field] = reused

        return protected

    def reveal_runtime_config(self, config: dict[str, object]) -> dict[str, object]:
        """Return plaintext secrets for connector and runtime use."""

        runtime_config: dict[str, object] = {}
        for raw_key, value in config.items():
            key = str(raw_key)
            runtime_config[key] = (
                self._reveal_secret_value(value) if key in SECRET_FIELD_NAMES else value
            )
        return runtime_config

    def redact_admin_config(self, config: dict[str, object]) -> dict[str, object]:
        """Return admin-safe config values without exposing persisted plaintext secrets."""

        admin_config: dict[str, object] = {}
        for raw_key, value in config.items():
            key = str(raw_key)
            admin_config[key] = (
                self._redact_secret_value(value) if key in SECRET_FIELD_NAMES else value
            )
        return admin_config

    def _protect_secret_value(
        self,
        value: object,
        *,
        previous: object,
    ) -> object:
        if self._is_encrypted_secret(value):
            return self._reuse_previous_secret(value)
        if self._should_preserve_secret(value):
            return self._reuse_previous_secret(previous)
        return self._encrypt_secret(str(value))

    def _reuse_previous_secret(self, value: object) -> object:
        if self._is_encrypted_secret(value):
            if value.get("version") == 2:
                return value
            return self._encrypt_secret(str(self._reveal_secret_value(value)))
        if self._is_plain_secret(value):
            return self._encrypt_secret(str(value))
        return _OMIT

    def _reveal_secret_value(self, value: object) -> object:
        if self._is_encrypted_secret(value):
            return decrypt_fernet_envelope(
                value,
                secret=self._credential_encryption_key,
            ).decode()
        return value

    def _redact_secret_value(self, value: object) -> object:
        if self._is_encrypted_secret(value) or self._is_plain_secret(value):
            return {
                "kind": SECRET_PLACEHOLDER_KIND,
                "configured": True,
            }
        return value

    def _encrypt_secret(self, value: str) -> EncryptedSecret:
        envelope = encrypt_fernet_envelope(
            value.encode(),
            secret=self._credential_encryption_key,
            iterations=self._kdf_iterations,
        )
        version = envelope["version"]
        iterations = envelope["iterations"]
        if not isinstance(version, int) or not isinstance(iterations, int):
            raise TypeError("Invalid encrypted secret envelope")
        return {
            "kind": "encrypted_secret",
            "ciphertext": str(envelope["ciphertext"]),
            "version": version,
            "kdf": str(envelope["kdf"]),
            "salt": str(envelope["salt"]),
            "iterations": iterations,
        }

    def _encrypt_secret_legacy_for_tests(self, value: str) -> EncryptedSecret:
        return {
            "kind": "encrypted_secret",
            "ciphertext": Fernet(
                derive_legacy_fernet_key(self._credential_encryption_key)
            ).encrypt(value.encode()).decode(),
        }

    def _should_preserve_secret(self, value: object) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        return self._is_secret_placeholder(value)

    def _is_encrypted_secret(self, value: object) -> TypeGuard[EncryptedSecret]:
        return (
            isinstance(value, dict)
            and value.get("kind") == SECRET_ENVELOPE_KIND
            and isinstance(value.get("ciphertext"), str)
        )

    def _is_secret_placeholder(self, value: object) -> TypeGuard[SecretPlaceholder]:
        return (
            isinstance(value, dict)
            and value.get("kind") == SECRET_PLACEHOLDER_KIND
            and value.get("configured") is True
        )

    def _is_plain_secret(self, value: object) -> bool:
        return isinstance(value, str) and value != ""
