"""Offline contracts for WhatsApp estimate decisions and payment QR payloads."""

import hashlib
import hmac
import json
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI
from mongomock_motor import AsyncMongoMockClient

from services.lifecycle_policy import LifecyclePolicy, digest, instruction_preview
from services.whatsapp_service import (
    ACTION_CATALOG,
    ACTIVE_CATALOG,
    SnapshotError,
    WhatsAppService,
    decode_estimate_action,
    estimate_action_token,
    lifecycle_event,
    message_payload,
    webhook_router,
)
from test_lifecycle_v3 import ACTIVE, VERIFIED

NOW = datetime(2026, 11, 21, 6, 0, tzinfo=timezone.utc)
SECRET = "estimate-action-test-secret-at-least-32-bytes"
PHONE = VERIFIED["phone"]
TEMPLATES = {
    key: {
        "name": item["name"], "language": item["language"], "category": "UTILITY",
        "parameters": item["parameters"], "approval_status": "approved",
        **({"header_format": item["header_format"]} if item.get("header_format") else {}),
    }
    for key, item in ACTIVE_CATALOG.items()
}
SETTINGS = replace(ACTIVE, templates=TEMPLATES, estimate_actions_enabled=True,
                   estimate_action_secret=SECRET)


def estimate():
    return {"parts": [], "labor": 1000, "diagnostic_fee": 0,
            "incoming_logistics_cost": 0, "return_shipping_cost": 0,
            "other_charges": 0, "tax": 0, "total": 1000, "status": "SENT"}


def repair(settings=SETTINGS):
    policy = LifecyclePolicy(None, settings, clock=lambda: NOW)
    return {
        "id": "repair-action", "repair_request_number": "REP-10008",
        "user_id": VERIFIED["user_id"], "status": "ESTIMATE_SENT", "revision": 4,
        "estimate": estimate(),
        "whatsapp_consent": {
            "opted_in": True, "version": 2, "revision": 0,
            "source": "repair_submission_v2", "scope_id": policy.scope_id(),
            "destination": PHONE, "phone_generation": 0,
            "activation_id": settings.activation_id, "at": NOW.isoformat(),
        },
    }


def test_actionable_payload_has_ordered_signed_buttons_and_tamper_rejected():
    job = lifecycle_event(repair(), "ESTIMATE_SENT", "evt-estimate", SETTINGS, VERIFIED)
    payload = message_payload(job, SETTINGS)
    assert job["template_key"] == "ESTIMATE_SENT_ACTIONABLE"
    buttons = [item for item in payload["template"]["components"] if item["type"] == "button"]
    assert [button["index"] for button in buttons] == ["0", "1"]
    claims = [decode_estimate_action(button["parameters"][0]["payload"], SETTINGS) for button in buttons]
    assert [claim["a"] for claim in claims] == ["approve", "decline"]
    token = buttons[0]["parameters"][0]["payload"]
    assert len(token) <= 256
    with pytest.raises(SnapshotError):
        decode_estimate_action(token[:-1] + ("A" if token[-1] != "A" else "B"), SETTINGS)


def test_payment_qr_is_exact_reviewed_header_and_feature_has_text_fallback():
    qr_settings = replace(SETTINGS, payment_qr_enabled=True,
                          payment_qr_url="https://evchargerrepair.in/assets/rushx-merchant-qr.png")
    r = repair(qr_settings)
    r.update(status="REPAIR_COMPLETED", payment_summary={
        "amount_due": "500.00", "balance_state": "BALANCE_VERIFIED", "currency": "INR",
        "verified_at": NOW.isoformat(), "verified_by": "admin",
    })
    job = lifecycle_event(r, "REPAIR_RESULT", "evt-complete", qr_settings, VERIFIED)
    payload = message_payload(job, qr_settings)
    assert job["template_key"] == "REPAIR_RESULT_DUE_QR"
    assert payload["template"]["components"][0]["parameters"][0]["image"]["link"] == qr_settings.payment_qr_url
    fallback = lifecycle_event(r, "REPAIR_RESULT", "evt-complete", SETTINGS, VERIFIED)
    assert fallback["template_key"] == "REPAIR_RESULT_DUE"


def test_signed_webhook_decision_is_sanitized_and_applied_once():
  async def scenario():
    db = AsyncMongoMockClient(tz_aware=True).test
    policy = LifecyclePolicy(db, SETTINGS, clock=lambda: NOW)
    await db.whatsapp_control.insert_one({
        "_id": policy.scope_id(), "activation_id": SETTINGS.activation_id,
        "paused": False, "mode": SETTINGS.mode,
        "manifest_digest": digest(SETTINGS.templates),
        "instructions_digest": digest(instruction_preview(SETTINGS)),
        "heartbeat_at": NOW,
    })
    await db.users.insert_one(dict(VERIFIED))
    r = repair()
    await db.repair_requests.insert_one(r)
    job = lifecycle_event(r, "ESTIMATE_SENT", "evt-estimate", SETTINGS, VERIFIED)
    job.update(state="sent", message_id="wamid.estimate", accepted_at=NOW,
               created_at=NOW, next_attempt_at=NOW, attempts=1)
    await db.whatsapp_jobs.insert_one(job)
    token = estimate_action_token(job, "approve", SETTINGS)
    body = {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": SETTINGS.phone_number_id},
        "messages": [{"from": PHONE.lstrip("+"), "id": "wamid.reply",
                      "context": {"id": "wamid.estimate"}, "type": "button",
                      "button": {"payload": token, "text": "Approve estimate"}}],
    }}]}]}
    raw = json.dumps(body).encode()
    signature = "sha256=" + hmac.new(SETTINGS.app_secret.encode(), raw, hashlib.sha256).hexdigest()
    app = FastAPI()
    app.include_router(webhook_router(lambda: db, lambda: SETTINGS), prefix="/api")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(2):
            response = await client.post("/api/webhooks/whatsapp", content=raw,
                                         headers={"x-hub-signature-256": signature})
            assert response.status_code == 200
    inbox = await db.whatsapp_action_inbox.find({}).to_list(10)
    assert len(inbox) == 1
    assert "payload" not in inbox[0] and "from" not in inbox[0] and "text" not in inbox[0]
    await db.whatsapp_action_inbox.update_one({}, {"$set": {"next_attempt_at": NOW}})
    service = WhatsAppService(db, SETTINGS, clock=lambda: NOW)
    assert await service.apply_estimate_actions() is True
    updated = await db.repair_requests.find_one({"id": r["id"]})
    assert updated["status"] == "CUSTOMER_APPROVED"
    assert updated["estimate"]["decision_audit"]["channel"] == "whatsapp"
    assert updated["estimate"]["decision_audit"]["estimate_fingerprint"] == job["fact_digest"]
    assert updated["revision"] == 5
    assert await service.apply_estimate_actions() is False
    assert await db.whatsapp_action_inbox.count_documents({"state": "applied"}) == 1
  asyncio.run(scenario())

