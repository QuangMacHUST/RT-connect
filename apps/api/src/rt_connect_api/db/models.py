"""Foundational scoped entities needed by P1 synthetic data only."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
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
    sites: Mapped[list[Site]] = relationship(back_populates="organization")


class Site(TimestampedIdMixin, Base):
    __tablename__ = "sites"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    organization: Mapped[Organization] = relationship(back_populates="sites")
    machines: Mapped[list[Machine]] = relationship(back_populates="site")


class Machine(TimestampedIdMixin, Base):
    __tablename__ = "machines"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    site_id: Mapped[UUID] = mapped_column(
        ForeignKey("sites.id"), nullable=False, index=True
    )
    stable_machine_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    site: Mapped[Site] = relationship(back_populates="machines")
