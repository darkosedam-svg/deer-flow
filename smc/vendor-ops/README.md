# vendor-ops

Payment → entitlement → access stack (Plan B M6). FastAPI service that turns
Lemon Squeezy webhooks into an entitlements table and a **manual ops queue**
for TradingView invite-only access grants/revokes (no public API exists —
the queue is the design, not a stopgap).

## Implemented

- `POST /webhooks/lemonsqueezy` — HMAC-SHA256 verified (raw body,
  `X-Signature`), idempotent by event id, maps products → tiers
  (founding→lifetime Pro, Core, Pro), creates grant/revoke ops items.
- `GET /ops/queue` / `POST /ops/queue/{id}/done` — the manual work list.
- Founding (lifetime) entitlements are immune to subscription churn events.
- Missing `tv_username` surfaces visibly in the queue instead of dropping.

## Not yet (before the M6 live-purchase gate, Mon 14 Sep)

- Celery worker: welcome email, Discord role sync.
- Nightly reconciliation vs TradingView access-list snapshot.
- Alembic migrations (schema still moving).
- Admin auth on the ops endpoints (must exist before deploy!).

## Run

```bash
uv sync --extra dev
uv run pytest
LEMONSQUEEZY_SIGNING_SECRET=... uv run uvicorn app.main:app
```

Set `DATABASE_URL` for Postgres in production; SQLite is the dev default.
**Checkout requirement:** `tv_username` must be a required custom field on
every Lemon Squeezy product — activation friction otherwise (Plan B risk
register).
