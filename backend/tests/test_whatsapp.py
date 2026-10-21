"""Offline HTTP + Mongo mocks: no actual WhatsApp messages or credentials."""

import asyncio
import hashlib
import hmac
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from mongomock_motor import AsyncMongoMockClient

from services.whatsapp_service import (
    Settings,
    WhatsAppService,
    consent_record,
    event_for,
    message_payload,
    ConfigurationError,
    STATUS_TEXT,
    CATALOG,
    webhook_router,
)

PHONE = "+919876543210"
USER = {
    "user_id": "customer",
    "role": "customer",
    "phone": PHONE,
    "name": "Sample Customer",
}
ADMIN = {"user_id": "admin", "role": "admin"}
SETTINGS = Settings(
    enabled=True,
    access_token="test-secret-token",
    phone_number_id="12345",
    test_phone_number_id="12345",
    app_secret="test-app-secret",
    verify_token="test-verify-secret",
    api_version="v23.0",
    dispatch_address="TEST configured dispatch address",
    test_recipients=(PHONE,),
    templates={
        status: {
            "name": spec["name"],
            "language": "en_US",
            "category": "UTILITY",
            "approval_status": "approved",
            "parameters": spec["parameters"],
        }
        for status, spec in CATALOG.items()
    },
)


def run(fn):
    asyncio.run(fn())


async def fixture(handler=None, settings=SETTINGS):
    mongo = AsyncMongoMockClient(tz_aware=True).test
    db = SimpleNamespace(
        repair_requests=mongo.repair_requests,
        whatsapp_jobs=mongo.whatsapp_jobs,
        whatsapp_receipts=mongo.whatsapp_receipts,
        whatsapp_control=mongo.whatsapp_control,
    )
    clock = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    calls = []

    def capture(request):
        calls.append(request)
        return (
            handler(request)
            if handler
            else httpx.Response(200, json={"messages": [{"id": "wamid.test"}]})
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(capture))
    svc = WhatsAppService(db, settings, http, clock=lambda: clock[0])
    await svc.initialize()
    repair = {
        "id": "r1",
        "repair_request_number": "REP-10001",
        "charger_info": {"brand": "Test", "model": "AC"},
        "whatsapp_consent": consent_record(True, USER, clock[0].isoformat()),
    }
    event = event_for(repair, "REQUESTED", "e1", settings, customer=USER)
    repair["whatsapp_outbox"] = [event] if event else []
    await db.repair_requests.insert_one(repair)
    await svc.reconcile()
    return db, svc, clock, calls, http


@pytest.mark.parametrize(
    "phone", ["", "9876543210", "+0123456789", "secret", "+1234567890123456"]
)
def test_invalid_consent_number(phone):
    with pytest.raises(Exception) as error:
        consent_record(True, {**USER, "phone": phone}, "now")
    assert error.value.status_code == 422


def test_settings_default_off_and_secrets_not_in_repr(monkeypatch):
    for name in ["WHATSAPP_ENABLED", "WHATSAPP_API_VERSION", "WHATSAPP_TEMPLATES_JSON"]:
        monkeypatch.delenv(name, raising=False)
    assert Settings.from_env().enabled is False
    monkeypatch.setenv("WHATSAPP_TEMPLATES_JSON", "broken")
    assert Settings.from_env().templates == {}
    for secret in [SETTINGS.access_token, SETTINGS.app_secret, SETTINGS.verify_token]:
        assert secret not in repr(SETTINGS)


def test_reconcile_idempotency_and_async_payload():
    async def scenario():
        db, svc, _, calls, http = await fixture()
        async with http:
            job = await db.whatsapp_jobs.find_one({})
            assert job["_id"] == "r1:REQUESTED"
            assert job["values"]["repair_number"] == "REP-10001"
            await db.repair_requests.update_one(
                {"id": "r1"},
                {
                    "$push": {
                        "whatsapp_outbox": {
                            k: job[k]
                            for k in [
                                "_id",
                                "repair_id",
                                "event_id",
                                "status",
                                "destination",
                                "consent_at",
                                "values",
                            ]
                        }
                    }
                },
            )
            await asyncio.gather(svc.reconcile(), svc.reconcile())
            assert await db.whatsapp_jobs.count_documents({}) == 1
            await asyncio.gather(svc.process_one(), svc.process_one())
            assert len(calls) == 1
            payload = json.loads(calls[0].content)
            assert payload["to"] == PHONE
            assert payload["biz_opaque_callback_data"] == job["_id"]
            assert (
                payload["template"]["components"][0]["parameters"][1]["text"]
                == "REP-10001"
            )
            sent = await db.whatsapp_jobs.find_one({})
            assert sent["state"] == "sent" and sent["delivery_rank"] == 0
            assert sent["message_id"] == "wamid.test"
            assert not await svc.process_one()

    run(scenario)


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retry_backoff_rate_limits_and_bounded_attempts(status):
    async def scenario():
        db, svc, clock, calls, http = await fixture(
            lambda _: httpx.Response(
                status, headers={"Retry-After": "90"}, text="secret provider error body"
            )
        )
        async with http:
            for attempt in range(1, 6):
                assert await svc.process_one()
                job = await db.whatsapp_jobs.find_one({})
                assert job["attempts"] == attempt
                assert job["state"] == (
                    "dead_letter" if attempt == 5 else "retryable_failure"
                )
                assert not await svc.process_one()
                assert (job["next_attempt_at"] - clock[0]).total_seconds() >= (
                    90 if status == 429 else 30
                )
                clock[0] = job["next_attempt_at"]
            assert len(calls) == 5
            assert "secret provider error body" not in str(job)

    run(scenario)


def test_network_timeout_and_permanent_error():
    async def scenario():
        def timeout(request):
            raise httpx.ReadTimeout("sensitive detail", request=request)

        db, svc, _, calls, http = await fixture(timeout)
        async with http:
            await svc.process_one()
            job = await db.whatsapp_jobs.find_one({})
            assert (
                job["state"] == "dead_letter"
                and job["error_code"] == "ambiguous_delivery"
            )
            assert "sensitive detail" not in str(job)
        db, svc, _, calls, http = await fixture(
            lambda _: httpx.Response(400, text="secret")
        )
        async with http:
            await svc.process_one()
            assert (await db.whatsapp_jobs.find_one({}))["state"] == "dead_letter"

    run(scenario)


def test_lease_recovery_after_restart_and_exhaustion():
    async def scenario():
        db, svc, clock, calls, http = await fixture()
        async with http:
            await db.whatsapp_jobs.update_one(
                {},
                {
                    "$set": {
                        "state": "processing",
                        "attempts": 1,
                        "lease": "old",
                        "lease_until": clock[0] + timedelta(seconds=120),
                    }
                },
            )
            assert not await svc.process_one()
            clock[0] += timedelta(seconds=121)
            restarted = WhatsAppService(db, SETTINGS, http, clock=lambda: clock[0])
            assert await restarted.process_one()
            assert len(calls) == 1
            await db.whatsapp_jobs.update_one(
                {},
                {
                    "$set": {
                        "state": "processing",
                        "attempts": 5,
                        "dispatch_started_at": None,
                        "lease_until": clock[0] - timedelta(seconds=1),
                    }
                },
            )
            await restarted.process_one()
            assert len(calls) == 1
            assert (await db.whatsapp_jobs.find_one({}))[
                "error_code"
            ] == "attempts_exhausted"

    run(scenario)


@pytest.mark.parametrize(
    "change",
    [
        dict(access_token=""),
        dict(api_version="bad/path"),
        dict(templates={}),
        dict(test_phone_number_id=""),
        dict(test_recipients=()),
        dict(mode="bad"),
        dict(app_secret=""),
    ],
)
def test_missing_config_never_sends(change):
    async def scenario():
        db, svc, _, calls, http = await fixture(settings=replace(SETTINGS, **change))
        async with http:
            await svc.process_one()
            assert calls == []
            assert (await db.whatsapp_jobs.find_one({}))[
                "error_code"
            ] == "configuration_invalid"

    run(scenario)


def test_disabled_and_revoked_consent_never_send():
    async def scenario():
        db, svc, _, calls, http = await fixture()
        async with http:
            svc.settings = replace(SETTINGS, enabled=False)
            assert not await svc.process_one()
            svc.settings = SETTINGS
            await db.repair_requests.update_one(
                {}, {"$set": {"whatsapp_consent.opted_in": False}}
            )
            await svc.process_one()
            assert calls == []
            assert (await db.whatsapp_jobs.find_one({}))[
                "error_code"
            ] == "consent_invalid"

    run(scenario)


def test_sandbox_template_and_parameter_order():
    async def scenario():
        db, _, _, _, http = await fixture()
        await http.aclose()
        job = await db.whatsapp_jobs.find_one({})
        sandbox = replace(
            SETTINGS,
            templates={
                "REQUESTED": {
                    "name": "hello_world",
                    "language": "en_US",
                    "parameters": [],
                }
            },
        )
        assert "components" not in message_payload(job, sandbox)["template"]
        with pytest.raises(ConfigurationError):
            message_payload(job, replace(sandbox, mode="production"))
        configured = replace(
            SETTINGS,
            templates={
                "REQUESTED": {
                    "name": "rushx_confirmation",
                    "language": "en",
                    "parameters": ["dispatch_address", "repair_number"],
                }
            },
        )
        with pytest.raises(ConfigurationError):
            message_payload(job, configured)
        params = message_payload(job, SETTINGS)["template"]["components"][0][
            "parameters"
        ]
        assert [p["text"] for p in params] == [USER["name"], "REP-10001", "Test AC"]

    run(scenario)


def receipt_payload(status="delivered", mid="wamid.test", callback=None):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": SETTINGS.phone_number_id},
                            "statuses": [
                                {
                                    "id": mid,
                                    "status": status,
                                    "timestamp": "1767225600",
                                    "biz_opaque_callback_data": callback,
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }


def test_webhook_signature_verification_dedup_order_and_early_receipt():
    async def scenario():
        db, svc, _, calls, http = await fixture()
        app = FastAPI()
        app.include_router(webhook_router(lambda: db, lambda: SETTINGS), prefix="/api")
        async with http, httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as browser:
            url = "/api/webhooks/whatsapp"
            response = await browser.get(
                url,
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": SETTINGS.verify_token,
                    "hub.challenge": "123",
                },
            )
            assert response.status_code == 200 and response.text == "123"
            assert (
                await browser.get(
                    url, params={"hub.mode": "subscribe", "hub.verify_token": "wrong"}
                )
            ).status_code == 403
            assert (await browser.post(url, json={})).status_code == 401

            async def post(data, tamper=False):
                raw = json.dumps(data).encode()
                signature = (
                    "sha256="
                    + hmac.new(
                        SETTINGS.app_secret.encode(), raw, hashlib.sha256
                    ).hexdigest()
                )
                return await browser.post(
                    url,
                    content=raw + (b" " if tamper else b""),
                    headers={"X-Hub-Signature-256": signature},
                )

            assert (await post(receipt_payload(), tamper=True)).status_code == 401
            # Persisted before HTTP response; callback correlates even without a stored message_id.
            for status in ["read", "read", "delivered", "sent", "failed"]:
                assert (
                    await post(receipt_payload(status, callback="r1:REQUESTED"))
                ).status_code == 200
            assert await db.whatsapp_receipts.count_documents({}) == 4
            svc.clock = lambda: datetime.now(timezone.utc)
            await svc.apply_receipts()
            await svc.apply_receipts()
            assert (await db.whatsapp_jobs.find_one({}))["state"] == "read"
            assert not await svc.process_one() and not calls
            assert (
                await post(
                    {
                        "object": "whatsapp_business_account",
                        "entry": [
                            {
                                "changes": [
                                    {
                                        "value": {
                                            "messages": [{"text": {"body": "hello"}}]
                                        }
                                    }
                                ]
                            }
                        ],
                    }
                )
            ).status_code == 200

    run(scenario)


def test_api_creation_consent_transitions_and_origin_security(monkeypatch):
    # Existing app routes exercised with dependency overrides and a Mongo mock.
    import server

    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).test
        actor = [USER]
        app = FastAPI()
        app.include_router(server.api_router)
        app.middleware("http")(server.trusted_origin)
        app.dependency_overrides[server.get_current_user] = lambda: actor[0]
        body = {
            "problem_description": "Charger not working",
            "charger_info": {"brand": "Test"},
        }
        with patch.object(server, "db", db), patch.object(
            server.WhatsAppSettings, "from_env", return_value=SETTINGS
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
                headers={"Origin": server.auth_settings.origins[0]},
            ) as browser:
                no_consent = await browser.post("/api/repairs", json=body)
                assert no_consent.status_code == 200
                assert (
                    await db.repair_requests.find_one({"id": no_consent.json()["id"]})
                )["whatsapp_outbox"] == []
                assert (
                    await browser.post(
                        "/api/repairs", json={**body, "whatsapp_opt_in": "true"}
                    )
                ).status_code == 422
                actor[0] = {**USER, "phone": "invalid"}
                assert (
                    await browser.post(
                        "/api/repairs", json={**body, "whatsapp_opt_in": True}
                    )
                ).status_code == 422
                actor[0] = USER
                response = await browser.post(
                    "/api/repairs",
                    json={
                        **body,
                        "whatsapp_opt_in": True,
                        "destination": "+19999999999",
                    },
                )
                assert response.status_code == 200
                repair = response.json()
                assert (
                    "whatsapp_outbox" not in repair and "whatsapp_consent" not in repair
                )
                rid = repair["id"]
                stored = await db.repair_requests.find_one({"id": rid})
                assert stored["whatsapp_consent"]["destination"] == PHONE
                assert stored["whatsapp_consent"]["source"] == "repair_submission_v1"
                assert len(stored["whatsapp_outbox"]) == 1
                endpoint = f"/api/repairs/{rid}/status"
                assert (
                    await browser.patch(endpoint, json={"status": "REPAIR_COMPLETED"})
                ).status_code == 400
                for status in ["AWAITING_SHIPMENT", "IN_TRANSIT_TO_VOLTX"]:
                    assert (
                        await browser.patch(endpoint, json={"status": status})
                    ).status_code == 200
                assert (
                    await browser.patch(endpoint, json={"status": "RECEIVED_AT_VOLTX"})
                ).status_code == 403
                actor[0] = ADMIN
                assert (
                    await browser.patch(
                        endpoint,
                        json={
                            "status": "RECEIVED_AT_VOLTX",
                            "note": "private technician note",
                        },
                    )
                ).status_code == 200
                assert (
                    await browser.patch(endpoint, json={"status": "RECEIVED_AT_VOLTX"})
                ).status_code == 400
                stored = await db.repair_requests.find_one({"id": rid})
                assert len(stored["whatsapp_outbox"]) == 3
                event = stored["whatsapp_outbox"][-1]
                assert (
                    event["_id"] == f"{rid}:{stored['status_history'][-1]['event_id']}"
                )
                assert CATALOG[event["status"]]["name"].startswith("rushx_")
                assert "Voltx" not in CATALOG[event["status"]]["body"]
                assert "private technician note" not in str(event)
                # Callback is exempt from browser Origin, but not signature authentication.
                assert (
                    await browser.post(
                        "/api/webhooks/whatsapp", headers={"Origin": ""}, json={}
                    )
                ).status_code == 401
                assert (
                    await browser.post(
                        "/api/repairs", headers={"Origin": ""}, json=body
                    )
                ).status_code == 403

    run(scenario)


@pytest.mark.parametrize("code", [4, 80007, 130429, 131056])
def test_meta_throttling_code_retries_without_storing_error_body(code):
    async def scenario():
        db, svc, _, _, http = await fixture(
            lambda _: httpx.Response(
                400, json={"error": {"code": code, "message": "secret"}}
            )
        )
        async with http:
            await svc.process_one()
            job = await db.whatsapp_jobs.find_one({})
            assert (
                job["state"] == "retryable_failure"
                and job["error_code"] == f"meta_{code}"
            )
            assert "secret" not in str(job)

    run(scenario)


def test_reconciliation_crash_after_upsert_is_recoverable():
    async def scenario():
        from unittest.mock import AsyncMock

        db, svc, _, _, http = await fixture()
        await http.aclose()
        repair = await db.repair_requests.find_one({})
        event = event_for(repair, "RECEIVED_AT_VOLTX", "e2", SETTINGS)
        await db.repair_requests.update_one({}, {"$push": {"whatsapp_outbox": event}})
        with patch.object(
            db.repair_requests,
            "update_one",
            AsyncMock(side_effect=RuntimeError("crash")),
        ):
            with pytest.raises(RuntimeError):
                await svc.reconcile()
        assert await db.whatsapp_jobs.count_documents({}) == 2
        assert len((await db.repair_requests.find_one({}))["whatsapp_outbox"]) == 1
        await svc.reconcile()
        assert await db.whatsapp_jobs.count_documents({}) == 2
        assert (await db.repair_requests.find_one({}))["whatsapp_outbox"] == []

    run(scenario)


def test_invalid_success_response_does_not_automatically_resend():
    async def scenario():
        db, svc, _, calls, http = await fixture(lambda _: httpx.Response(200, json={}))
        async with http:
            await svc.process_one()
            assert not await svc.process_one()
            assert len(calls) == 1
            assert (await db.whatsapp_jobs.find_one({}))[
                "error_code"
            ] == "ambiguous_response"

    run(scenario)


def test_racing_status_transition_creates_one_event():
    import server

    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).test
        db = SimpleNamespace(repair_requests=db.repair_requests, users=db.users)
        consent = consent_record(True, USER, "2026-01-01T00:00:00+00:00")
        await db.repair_requests.insert_one(
            {
                "id": "race",
                "user_id": USER["user_id"],
                "repair_request_number": "REP-20000",
                "status": "IN_TRANSIT_TO_VOLTX",
                "status_history": [],
                "whatsapp_consent": consent,
                "whatsapp_outbox": [],
            }
        )
        original = db.repair_requests.find_one
        ready, readers = asyncio.Event(), [0]

        async def read_barrier(*args, **kwargs):
            result = await original(*args, **kwargs)
            if result["status"] == "IN_TRANSIT_TO_VOLTX":
                readers[0] += 1
                if readers[0] == 2:
                    ready.set()
                await ready.wait()
            return result

        with patch.object(server, "db", db), patch.object(
            server.WhatsAppSettings, "from_env", return_value=SETTINGS
        ), patch.object(db.repair_requests, "find_one", read_barrier):
            results = await asyncio.gather(
                *[
                    server.update_repair_status(
                        "race",
                        server.RepairStatusUpdate(status="RECEIVED_AT_VOLTX"),
                        ADMIN,
                    )
                    for _ in range(2)
                ],
                return_exceptions=True,
            )
        assert sum(isinstance(result, dict) for result in results) == 1
        assert [
            result.status_code for result in results if isinstance(result, Exception)
        ] == [409]
        repair = await original({"id": "race"})
        assert len(repair["status_history"]) == len(repair["whatsapp_outbox"]) == 1

    run(scenario)


def test_all_relevant_transitions_keep_private_fields_out_of_jobs():
    import server

    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).test
        with patch.object(server, "db", db), patch.object(
            server.WhatsAppSettings, "from_env", return_value=SETTINGS
        ):
            repair = await server.create_repair(
                server.RepairCreate(
                    whatsapp_opt_in=True,
                    charger_info={"brand": "Test"},
                    problem_description="Not working",
                ),
                USER,
            )
            rid = repair["id"]
            statuses = [
                "AWAITING_SHIPMENT",
                "IN_TRANSIT_TO_VOLTX",
                "RECEIVED_AT_VOLTX",
                "DIAGNOSING",
                "ESTIMATE_SENT",
                "CUSTOMER_APPROVED",
                "REPAIRING",
                "REPAIR_COMPLETED",
                "PAYMENT_PENDING",
                "READY_TO_SHIP",
                "SHIPPED_TO_CUSTOMER",
                "DELIVERED",
                "COMPLETED",
            ]
            for status in statuses:
                if status == "ESTIMATE_SENT":
                    await db.repair_requests.update_one(
                        {"id": rid},
                        {
                            "$set": {
                                "estimate": {
                                    "total": 100,
                                    "labor": 100,
                                    "status": "DRAFT",
                                    "notes": "sensitive estimate",
                                },
                                "diagnosis": {
                                    "technician_notes": "sensitive diagnosis"
                                },
                            }
                        },
                    )
                if status == "PAYMENT_PENDING":
                    await server.verify_repair_payment(
                        rid,
                        server.PaymentVerification(
                            amount_due=100, reference="test record"
                        ),
                        ADMIN,
                    )
                if status == "SHIPPED_TO_CUSTOMER":
                    await server.update_repair_shipment(
                        rid,
                        server.ShipmentUpdate(
                            leg="return",
                            courier="Test Courier",
                            tracking_number="SAMPLE123",
                        ),
                        ADMIN,
                    )
                await server.update_repair_status(
                    rid,
                    server.RepairStatusUpdate(status=status, note="sensitive note"),
                    ADMIN,
                )
            stored = await db.repair_requests.find_one({"id": rid})
            assert {e["status"] for e in stored["whatsapp_outbox"]} == set(STATUS_TEXT)
            assert len(stored["whatsapp_outbox"]) == len(STATUS_TEXT)
            assert "sensitive" not in str(stored["whatsapp_outbox"])

    run(scenario)


def test_webhook_unknown_ids_defer_without_blocking_other_receipts():
    async def scenario():
        db, svc, clock, _, http = await fixture()
        await http.aclose()
        for i in range(201):
            await db.whatsapp_receipts.insert_one(
                {
                    "_id": str(i),
                    "message_id": f"unknown-{i}",
                    "status": "sent",
                    "rank": 1,
                    "timestamp": "1",
                    "processed": False,
                    "next_check_at": clock[0],
                }
            )
        await db.whatsapp_receipts.insert_one(
            {
                "_id": "matched",
                "message_id": "wamid.test",
                "job_id": "r1:REQUESTED",
                "status": "failed",
                "rank": 2,
                "timestamp": "1",
                "processed": False,
                "next_check_at": clock[0],
            }
        )
        await svc.apply_receipts()
        await svc.apply_receipts()
        assert (await db.whatsapp_jobs.find_one({}))["state"] == "failed"

    run(scenario)


def test_uvicorn_access_log_redacts_verification_query():
    import logging
    from services.whatsapp_service import WebhookAccessLogFilter

    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        1,
        '%s - "%s %s HTTP/%s" %s',
        (
            "client",
            "GET",
            "/api/webhooks/whatsapp?hub.verify_token=private-token",
            "1.1",
            200,
        ),
        None,
    )
    assert WebhookAccessLogFilter().filter(record)
    assert "private-token" not in record.getMessage()
    assert "/api/webhooks/whatsapp" in record.getMessage()
