from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import DateTime, Enum, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Tier(enum.StrEnum):
    core = "core"
    pro = "pro"


class EntitlementStatus(enum.StrEnum):
    active = "active"
    revoked = "revoked"


class OpsAction(enum.StrEnum):
    grant = "grant"
    revoke = "revoke"


class OpsStatus(enum.StrEnum):
    pending = "pending"
    done = "done"


class WebhookEvent(Base):
    """Every received webhook, keyed by Lemon Squeezy event id — the
    idempotency ledger. Duplicates are acknowledged and dropped."""

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    event_name: Mapped[str] = mapped_column(String(64))
    raw_body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Entitlement(Base):
    __tablename__ = "entitlements"
    __table_args__ = (UniqueConstraint("customer_email", "tier", name="uq_customer_tier"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_email: Mapped[str] = mapped_column(String(255), index=True)
    tv_username: Mapped[str] = mapped_column(String(128))
    tier: Mapped[Tier] = mapped_column(Enum(Tier))
    status: Mapped[EntitlementStatus] = mapped_column(
        Enum(EntitlementStatus), default=EntitlementStatus.active
    )
    lifetime: Mapped[int] = mapped_column(Integer, default=0)  # founding member = 1
    ls_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ls_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    granted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class OpsItem(Base):
    """Manual TradingView access queue. A human works this list in the
    'Manage access' UI (no public API exists — Plan B M6 decision: build the
    queue, not browser automation). Revokes get the same visibility as grants."""

    __tablename__ = "ops_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[OpsAction] = mapped_column(Enum(OpsAction))
    tv_username: Mapped[str] = mapped_column(String(128))
    tier: Mapped[Tier] = mapped_column(Enum(Tier))
    reason: Mapped[str] = mapped_column(String(255))
    status: Mapped[OpsStatus] = mapped_column(Enum(OpsStatus), default=OpsStatus.pending)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    done_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
