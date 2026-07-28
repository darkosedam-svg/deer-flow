from __future__ import annotations

import datetime as dt

from fastapi import FastAPI, Header, HTTPException, Request

from app.db import get_session, init_db
from app.models import OpsItem, OpsStatus
from app.webhooks import process_event, verify_signature

app = FastAPI(title="vendor-ops")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request, x_signature: str = Header(default="")) -> dict:
    raw = await request.body()
    if not verify_signature(raw, x_signature):
        raise HTTPException(status_code=401, detail="invalid signature")
    session = get_session()
    try:
        result = process_event(session, raw)
    finally:
        session.close()
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "bad payload"))
    return result


@app.get("/ops/queue")
def ops_queue(status: str = "pending") -> list[dict]:
    session = get_session()
    try:
        items = (
            session.query(OpsItem)
            .filter(OpsItem.status == OpsStatus(status))
            .order_by(OpsItem.created_at)
            .all()
        )
        return [
            {
                "id": i.id,
                "action": i.action.value,
                "tv_username": i.tv_username,
                "tier": i.tier.value,
                "reason": i.reason,
                "created_at": i.created_at.isoformat(),
            }
            for i in items
        ]
    finally:
        session.close()


@app.post("/ops/queue/{item_id}/done")
def ops_done(item_id: int) -> dict:
    """Mark a grant/revoke as performed in the TradingView 'Manage access' UI."""
    session = get_session()
    try:
        item = session.get(OpsItem, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="no such item")
        item.status = OpsStatus.done
        item.done_at = dt.datetime.now(dt.UTC)
        session.commit()
        return {"ok": True}
    finally:
        session.close()
