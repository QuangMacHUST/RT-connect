"""Organization-scoped RT-CONNECT entities and lifecycle evidence."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    false,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rt_connect_api.db.base import Base


class TimestampedIdMixin:
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Organization(TimestampedIdMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    sites: Mapped[list[Site]] = relationship(back_populates="organization")
    memberships: Mapped[list[OrganizationMembership]] = relationship(back_populates="organization")


class UserIdentity(TimestampedIdMixin, Base):
    """Application projection of a Supabase identity; password material is never stored here."""

    __tablename__ = "user_identities"

    supabase_user_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    memberships: Mapped[list[OrganizationMembership]] = relationship(back_populates="user_identity")


class OrganizationMembership(TimestampedIdMixin, Base):
    """Membership defines organization scope, not an action-level role hierarchy."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "user_identity_id", name="uq_organization_memberships_identity"
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_identities.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    organization: Mapped[Organization] = relationship(back_populates="memberships")
    user_identity: Mapped[UserIdentity] = relationship(back_populates="memberships")


class Site(TimestampedIdMixin, Base):
    __tablename__ = "sites"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    organization: Mapped[Organization] = relationship(back_populates="sites")
    machines: Mapped[list[Machine]] = relationship(back_populates="site")


class Machine(TimestampedIdMixin, Base):
    __tablename__ = "machines"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id"), nullable=False, index=True)
    stable_machine_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="ACTIVE")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    site: Mapped[Site] = relationship(back_populates="machines")


class AuditEvent(TimestampedIdMixin, Base):
    """Append-only lifecycle evidence for organization-scoped changes."""

    __tablename__ = "audit_events"

    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    actor_user_identity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_identities.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True, index=True
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
