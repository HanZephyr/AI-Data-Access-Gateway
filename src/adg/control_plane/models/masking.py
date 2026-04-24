from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from adg.control_plane.models.base import Base
from adg.shared.ids import uuidv7


class MaskingPolicy(Base):
    __tablename__ = "masking_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuidv7)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    subject_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    subject_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)


class DecryptContext(Base):
    __tablename__ = "decrypt_contexts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuidv7)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    query_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    datasource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_fields_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
