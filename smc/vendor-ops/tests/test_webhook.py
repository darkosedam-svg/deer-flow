import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

SECRET = "test-secret"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("LEMONSQUEEZY_SIGNING_SECRET", SECRET)
    from app.db import reset_engine
    from app.main import app

    reset_engine()  # next engine use picks up the temp DATABASE_URL
    with TestClient(app) as c:
        yield c
    reset_engine()


def sign(body: bytes) -> str:
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def make_event(event_name, event_id, email="buyer@example.com", tv="darko_tv",
               variant="Founding Member (Lifetime Pro)", status="active", data_id="123"):
    return json.dumps(
        {
            "meta": {
                "event_name": event_name,
                "webhook_id": event_id,
                "custom_data": {"tv_username": tv},
            },
            "data": {
                "id": data_id,
                "attributes": {
                    "user_email": email,
                    "variant_name": variant,
                    "status": status,
                },
            },
        }
    ).encode()


def post(client, body):
    return client.post(
        "/webhooks/lemonsqueezy", content=body, headers={"X-Signature": sign(body)}
    )


def test_rejects_bad_signature(client):
    body = make_event("order_created", "evt-1")
    resp = client.post(
        "/webhooks/lemonsqueezy", content=body, headers={"X-Signature": "0" * 64}
    )
    assert resp.status_code == 401


def test_grant_creates_entitlement_and_ops_item(client):
    resp = post(client, make_event("order_created", "evt-1"))
    assert resp.status_code == 200 and resp.json()["ok"]
    queue = client.get("/ops/queue").json()
    assert len(queue) == 1
    assert queue[0]["action"] == "grant"
    assert queue[0]["tv_username"] == "darko_tv"
    assert queue[0]["tier"] == "pro"


def test_duplicate_event_is_idempotent(client):
    body = make_event("order_created", "evt-dup")
    assert post(client, body).json() == {"ok": True}
    assert post(client, body).json() == {"ok": True, "duplicate": True}
    assert len(client.get("/ops/queue").json()) == 1


def test_cancellation_creates_revoke_item(client):
    post(
        client,
        make_event("subscription_created", "evt-1", variant="Core Monthly", tv="churner"),
    )
    post(
        client,
        make_event("subscription_cancelled", "evt-2", variant="Core Monthly", tv="churner"),
    )
    queue = client.get("/ops/queue").json()
    actions = [(i["action"], i["tier"]) for i in queue]
    assert ("grant", "core") in actions
    assert ("revoke", "core") in actions


def test_founding_lifetime_survives_refund_noise(client):
    """A founding (lifetime) member must NOT be revoked by subscription events."""
    post(client, make_event("order_created", "evt-1"))
    post(client, make_event("subscription_expired", "evt-2"))
    queue = client.get("/ops/queue").json()
    assert [i["action"] for i in queue] == ["grant"]


def test_missing_tv_username_stays_visible(client):
    body = json.dumps(
        {
            "meta": {"event_name": "order_created", "webhook_id": "evt-x", "custom_data": {}},
            "data": {
                "id": "9",
                "attributes": {"user_email": "no-tv@example.com", "variant_name": "Core"},
            },
        }
    ).encode()
    post(client, body)
    queue = client.get("/ops/queue").json()
    assert "MISSING" in queue[0]["tv_username"]


def test_ops_done_flow(client):
    post(client, make_event("order_created", "evt-1"))
    item_id = client.get("/ops/queue").json()[0]["id"]
    assert client.post(f"/ops/queue/{item_id}/done").json() == {"ok": True}
    assert client.get("/ops/queue").json() == []
