"""Lemon Squeezy webhook processing.

Non-negotiables implemented here (Plan B M6):
- HMAC-SHA256 signature verification on the RAW body (X-Signature header).
- Idempotency via the event id; Lemon Squeezy retries.
- Cancellation/expiry/refund creates a REVOKE ops item with the same
  visibility as grants — unrevoked churn is the classic leak.

The TradingView username must arrive as a required checkout custom field
(`tv_username`); the fallback marker keeps missing ones visible in the queue
instead of silently dropping the grant.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Entitlement,
    EntitlementStatus,
    OpsAction,
    OpsItem,
    Tier,
    WebhookEvent,
)

SIGNING_SECRET_ENV = "LEMONSQUEEZY_SIGNING_SECRET"

GRANT_EVENTS = {"order_created", "subscription_created", "subscription_updated"}
REVOKE_EVENTS = {"subscription_cancelled", "subscription_expired", "order_refunded"}

# Variant name (lowercased substring) -> (tier, lifetime). Configure to match
# the Lemon Squeezy products. Founding member = lifetime Pro (Plan B §2).
PRODUCT_MAP: list[tuple[str, Tier, bool]] = [
    ("founding", Tier.pro, True),
    ("pro", Tier.pro, False),
    ("core", Tier.core, False),
]

MISSING_TV_USERNAME = "<MISSING — chase via email>"


def verify_signature(raw_body: bytes, signature: str, secret: str | None = None) -> bool:
    secret = secret if secret is not None else os.environ.get(SIGNING_SECRET_ENV, "")
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def _resolve_product(variant_name: str) -> tuple[Tier, bool] | None:
    name = variant_name.lower()
    for needle, tier, lifetime in PRODUCT_MAP:
        if needle in name:
            return tier, lifetime
    return None


def process_event(session: Session, raw_body: bytes) -> dict:
    payload = json.loads(raw_body)
    meta = payload.get("meta", {})
    event_name = meta.get("event_name", "")
    event_id = str(meta.get("webhook_id") or meta.get("event_id") or "")
    if not event_id:
        return {"ok": False, "error": "missing event id"}

    # Idempotency: seen this event before → acknowledge and do nothing.
    dup = session.execute(
        select(WebhookEvent).where(WebhookEvent.event_id == event_id)
    ).scalar_one_or_none()
    if dup is not None:
        return {"ok": True, "duplicate": True}
    session.add(
        WebhookEvent(event_id=event_id, event_name=event_name, raw_body=raw_body.decode())
    )

    attrs = payload.get("data", {}).get("attributes", {})
    custom = meta.get("custom_data") or {}
    email = attrs.get("user_email") or attrs.get("customer_email") or ""
    tv_username = (custom.get("tv_username") or "").strip() or MISSING_TV_USERNAME
    variant = attrs.get("variant_name") or attrs.get("product_name") or ""
    is_sub = "subscription" in event_name
    subscription_id = str(payload.get("data", {}).get("id", "")) if is_sub else None

    resolved = _resolve_product(variant)
    if resolved is None:
        session.commit()
        return {"ok": True, "ignored": f"unknown product {variant!r}"}
    tier, lifetime = resolved

    if event_name in GRANT_EVENTS:
        # subscription_updated only grants while the subscription is active.
        inactive = attrs.get("status") not in ("active", "on_trial")
        if event_name == "subscription_updated" and inactive:
            _revoke(session, email, tv_username, tier, reason=f"{event_name}:{attrs.get('status')}")
        else:
            _grant(session, email, tv_username, tier, lifetime, subscription_id, event_name)
    elif event_name in REVOKE_EVENTS:
        _revoke(session, email, tv_username, tier, reason=event_name)
    else:
        session.commit()
        return {"ok": True, "ignored": f"unhandled event {event_name!r}"}

    session.commit()
    return {"ok": True}


def _grant(
    session: Session,
    email: str,
    tv_username: str,
    tier: Tier,
    lifetime: bool,
    subscription_id: str | None,
    reason: str,
) -> None:
    ent = session.execute(
        select(Entitlement).where(
            Entitlement.customer_email == email, Entitlement.tier == tier
        )
    ).scalar_one_or_none()
    if ent is None:
        ent = Entitlement(customer_email=email, tv_username=tv_username, tier=tier)
        session.add(ent)
    ent.status = EntitlementStatus.active
    ent.tv_username = tv_username if tv_username != MISSING_TV_USERNAME else ent.tv_username
    ent.lifetime = 1 if lifetime else ent.lifetime
    ent.ls_subscription_id = subscription_id or ent.ls_subscription_id
    session.add(
        OpsItem(action=OpsAction.grant, tv_username=ent.tv_username, tier=tier, reason=reason)
    )


def _revoke(session: Session, email: str, tv_username: str, tier: Tier, reason: str) -> None:
    ent = session.execute(
        select(Entitlement).where(
            Entitlement.customer_email == email, Entitlement.tier == tier
        )
    ).scalar_one_or_none()
    if ent is not None:
        if ent.lifetime:
            return  # founding members keep lifetime access on subscription noise
        ent.status = EntitlementStatus.revoked
        tv_username = ent.tv_username
    session.add(
        OpsItem(action=OpsAction.revoke, tv_username=tv_username, tier=tier, reason=reason)
    )
