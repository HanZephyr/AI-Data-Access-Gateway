from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from adg.control_plane.models.base import Base
from adg.shared.ids import uuidv7


class Tag(Base):
    """Operator-defined label used to group and govern resources."""

    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuidv7)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class ResourceTag(Base):
    """Many-to-many binding between a resource and a tag."""

    __tablename__ = "resource_tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuidv7)
    tag_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


class DatasourceTag(Base):
    """Many-to-many binding between a datasource and a tag."""

    __tablename__ = "datasource_tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuidv7)
    tag_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    datasource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


class ResourcePolicy(Base):
    """Resource-level allow or deny rule for a user, role, group, or everyone."""

    __tablename__ = "resource_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuidv7)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    effect: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    datasource_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    tag_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    allow_decrypt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)


class FieldPolicy(Base):
    """Field-level allow or deny rule applied after resource access is granted."""

    __tablename__ = "field_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuidv7)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    effect: Mapped[str] = mapped_column(String(16), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
