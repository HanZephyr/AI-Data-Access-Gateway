import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.connectors.base import QueryResult
from adg.control_plane.models.masking import DecryptContext, MaskingPolicy
from adg.control_plane.models.resource import Resource
from adg.policy.runtime import IdentityContext
from adg.shared.errors import ValidationError
from adg.shared.ids import uuidv7


class MaskingService:
    def __init__(self, session: Session, *, secret_key: str) -> None:
        self._session = session
        self._secret_key = secret_key
        self._service_fernet = Fernet(self._derive_fernet_key(secret_key))

    def apply_to_result(
        self,
        *,
        identity: IdentityContext,
        datasource_id: str,
        query_id: str,
        resources: list[Resource],
        result: QueryResult,
    ) -> tuple[QueryResult, list[dict[str, str]]]:
        policies = self._matching_policies(identity=identity, resources=resources)
        masked_columns: list[dict[str, str]] = []
        rows: list[dict[str, object]] = []

        for row in result.rows:
            masked_row = dict(row)
            for policy in policies:
                if policy.field_name not in masked_row or masked_row[policy.field_name] is None:
                    continue
                if policy.strategy == "reversible":
                    masked_row[policy.field_name] = self.mask_reversible_value(
                        user_id=identity.user_id,
                        datasource_id=datasource_id,
                        query_id=query_id,
                        field_name=policy.field_name,
                        value=masked_row[policy.field_name],
                    )
                else:
                    masked_row[policy.field_name] = self.mask_plain_value(
                        masked_row[policy.field_name],
                        strategy=policy.strategy,
                        config=self._policy_config(policy),
                    )
                marker = {"name": policy.field_name, "strategy": policy.strategy}
                if marker not in masked_columns:
                    masked_columns.append(marker)
            rows.append(masked_row)

        return QueryResult(columns=result.columns, rows=rows), masked_columns

    def mask_plain_value(
        self,
        value: object,
        *,
        strategy: str,
        config: dict[str, object],
    ) -> str | None:
        if value is None:
            return None
        text = str(value)
        if strategy == "fixed":
            return str(config.get("replacement", "***"))
        if strategy == "partial":
            prefix = int(str(config.get("prefix", 2)))
            suffix = int(str(config.get("suffix", 2)))
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
        user_id: str | None,
        datasource_id: str,
        query_id: str,
        field_name: str,
        value: object,
        expires_at: datetime | None = None,
    ) -> str:
        context_id = uuidv7()
        temporary_key = Fernet.generate_key()
        temporary_fernet = Fernet(temporary_key)
        ciphertext = temporary_fernet.encrypt(str(value).encode()).decode()
        context = DecryptContext(
            id=context_id,
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
        user_id: str | None,
        values: list[str],
    ) -> list[str]:
        return [
            self._decrypt_marker(user_id=user_id, marker=value)
            for value in values
        ]

    def _decrypt_marker(self, *, user_id: str | None, marker: str) -> str:
        context_id, ciphertext = self._parse_marker(marker)
        context = self._session.get(DecryptContext, context_id)
        if context is None:
            raise ValidationError("Decrypt context not found")
        if context.user_id != user_id:
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

    def _matching_policies(
        self,
        *,
        identity: IdentityContext,
        resources: list[Resource],
    ) -> list[MaskingPolicy]:
        resource_ids = [resource.id for resource in resources]
        if not resource_ids:
            return []
        policies = self._session.execute(
            select(MaskingPolicy).where(
                MaskingPolicy.resource_id.in_(resource_ids),
                MaskingPolicy.status == "active",
            )
        ).scalars()
        return [policy for policy in policies if self._subject_matches(policy, identity)]

    def _subject_matches(self, policy: MaskingPolicy, identity: IdentityContext) -> bool:
        if policy.subject_type is None:
            return True
        if policy.subject_type == "all":
            return True
        if policy.subject_type == "user":
            return policy.subject_id == identity.user_id
        if policy.subject_type == "role":
            return policy.subject_id in identity.roles
        if policy.subject_type == "group":
            return policy.subject_id in identity.groups
        return False

    def _policy_config(self, policy: MaskingPolicy) -> dict[str, object]:
        loaded: Any = json.loads(policy.config_json)
        if not isinstance(loaded, dict):
            return {}
        return {str(key): value for key, value in loaded.items()}
