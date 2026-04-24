import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from adg.control_plane.models.masking import DecryptContext
from adg.shared.errors import ValidationError


class MaskingService:
    def __init__(self, session: Session, *, secret_key: str) -> None:
        self._session = session
        self._secret_key = secret_key
        self._service_fernet = Fernet(self._derive_fernet_key(secret_key))

    def mask_plain_value(
        self,
        value: object,
        *,
        strategy: str,
        config: dict[str, object],
    ) -> object:
        if value is None:
            return None
        text = str(value)
        if strategy == "fixed":
            return str(config.get("replacement", "***"))
        if strategy == "partial":
            prefix = int(config.get("prefix", 2))
            suffix = int(config.get("suffix", 2))
            fill = str(config.get("fill", "*"))[:1] or "*"
            if len(text) <= prefix + suffix:
                return fill * len(text)
            return f"{text[:prefix]}{fill * (len(text) - prefix - suffix)}{text[-suffix:]}"
        if strategy == "hash":
            return hashlib.sha256(f"{self._secret_key}:{text}".encode()).hexdigest()
        raise ValidationError(f"Unsupported masking strategy: {strategy}")

    def mask_reversible_value(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        datasource_id: str,
        query_id: str,
        field_name: str,
        value: object,
        expires_at: datetime | None = None,
    ) -> str:
        context_id = str(uuid4())
        temporary_key = Fernet.generate_key()
        temporary_fernet = Fernet(temporary_key)
        ciphertext = temporary_fernet.encrypt(str(value).encode()).decode()
        context = DecryptContext(
            id=context_id,
            tenant_id=tenant_id,
            query_id=query_id,
            user_id=user_id,
            datasource_id=datasource_id,
            key_ciphertext=self._service_fernet.encrypt(temporary_key).decode(),
            allowed_fields_json=json.dumps([field_name], separators=(",", ":")),
            expires_at=expires_at or datetime.now(UTC) + timedelta(minutes=15),
        )
        self._session.add(context)
        self._session.flush()
        return f"$adg_rev${context_id}${ciphertext}"

    def decrypt_values(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        values: list[str],
    ) -> list[str]:
        return [
            self._decrypt_marker(tenant_id=tenant_id, user_id=user_id, marker=value)
            for value in values
        ]

    def _decrypt_marker(self, *, tenant_id: str, user_id: str | None, marker: str) -> str:
        context_id, ciphertext = self._parse_marker(marker)
        context = self._session.get(DecryptContext, context_id)
        if context is None:
            raise ValidationError("Decrypt context not found")
        if context.tenant_id != tenant_id or context.user_id != user_id:
            raise ValidationError("Decrypt context does not match identity")
        if self._normalize_time(context.expires_at) <= datetime.now(UTC):
            raise ValidationError("Decrypt context expired")

        try:
            temporary_key = self._service_fernet.decrypt(context.key_ciphertext.encode())
            plaintext = Fernet(temporary_key).decrypt(ciphertext.encode()).decode()
        except InvalidToken as error:
            raise ValidationError("Decrypt value is invalid") from error
        return plaintext

    def _parse_marker(self, marker: str) -> tuple[str, str]:
        parts = marker.split("$", 3)
        if len(parts) != 4 or parts[0] != "" or parts[1] != "adg_rev":
            raise ValidationError("Invalid reversible value marker")
        return parts[2], parts[3]

    def _derive_fernet_key(self, secret_key: str) -> bytes:
        return base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode()).digest())

    def _normalize_time(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
