import base64
import hashlib
from typing import Final, Literal, TypedDict, TypeGuard

from cryptography.fernet import Fernet

from adg.app.settings import get_settings

SECRET_ENVELOPE_KIND: Final[str] = "encrypted_secret"
SECRET_PLACEHOLDER_KIND: Final[str] = "secret_placeholder"
SECRET_FIELD_NAMES: Final[frozenset[str]] = frozenset({"password"})
_OMIT = object()


class EncryptedSecret(TypedDict):
    kind: Literal["encrypted_secret"]
    ciphertext: str


class SecretPlaceholder(TypedDict):
    kind: Literal["secret_placeholder"]
    configured: bool


class SecretConfigService:
    """Protects persisted datasource secrets and reveals them only for runtime use."""

    def __init__(self, *, credential_encryption_key: str) -> None:
        self._fernet = Fernet(self._derive_fernet_key(credential_encryption_key))

    @classmethod
    def from_settings(cls) -> "SecretConfigService":
        """Build the service from the process-wide application settings."""

        return cls(credential_encryption_key=get_settings().credential_encryption_key)

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
            return value
        if self._should_preserve_secret(value):
            return self._reuse_previous_secret(previous)
        return self._encrypt_secret(str(value))

    def _reuse_previous_secret(self, value: object) -> object:
        if self._is_encrypted_secret(value):
            return value
        if self._is_plain_secret(value):
            return self._encrypt_secret(str(value))
        return _OMIT

    def _reveal_secret_value(self, value: object) -> object:
        if self._is_encrypted_secret(value):
            ciphertext = value.get("ciphertext")
            if isinstance(ciphertext, str):
                return self._fernet.decrypt(ciphertext.encode()).decode()
        return value

    def _redact_secret_value(self, value: object) -> object:
        if self._is_encrypted_secret(value) or self._is_plain_secret(value):
            return {
                "kind": SECRET_PLACEHOLDER_KIND,
                "configured": True,
            }
        return value

    def _encrypt_secret(self, value: str) -> EncryptedSecret:
        return {
            "kind": "encrypted_secret",
            "ciphertext": self._fernet.encrypt(value.encode()).decode(),
        }

    def _derive_fernet_key(self, credential_encryption_key: str) -> bytes:
        digest = hashlib.sha256(credential_encryption_key.encode()).digest()
        return base64.urlsafe_b64encode(digest)

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
