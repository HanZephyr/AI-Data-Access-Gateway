import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from adg.control_plane.models.base import Base
from adg.shared.ids import uuidv7
from adg.shared.secret_config import SecretConfigService


class Datasource(Base):
    """Stored connection definition for a database asset source."""

    __tablename__ = "datasources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuidv7)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    datasource_kind: Mapped[str] = mapped_column(String(64), nullable=False, default="relational")
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def persisted_config(self) -> dict[str, object]:
        """Decode the persisted JSON config into a dictionary without revealing secrets."""

        loaded: Any = json.loads(self.config_json)
        if not isinstance(loaded, dict):
            return {}
        return {str(key): value for key, value in loaded.items()}

    def config(self) -> dict[str, object]:
        """Return the connector/runtime config with persisted secrets decrypted."""

        return SecretConfigService.from_settings().reveal_runtime_config(self.persisted_config())

    def admin_config(self) -> dict[str, object]:
        """Return an admin-safe config payload without plaintext secrets."""

        return SecretConfigService.from_settings().redact_admin_config(self.persisted_config())
