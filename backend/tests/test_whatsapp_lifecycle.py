"""Issue #3: all lifecycle facts, production gates and delivery uncertainty use mocks."""

import asyncio
import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from mongomock_motor import AsyncMongoMockClient

import server
from services.whatsapp_service import (
    CATALOG,
    ConfigurationError,
    SnapshotError,
    WhatsAppService,
    message_payload,
    validate_settings,
    webhook_router,
)
from test_whatsapp import SETTINGS, USER, ADMIN, PHONE, fixture, receipt_payload, run

PATH = [
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
SELECTED = [
    "REQUESTED",
    "AWAITING_SHIPMENT",
    "RECEIVED_AT_VOLTX",
    "ESTIMATE_SENT",
    "CUSTOMER_APPROVED",
    "REPAIR_COMPLETED",
    "PAYMENT_PENDING",
    "SHIPPED_TO_CUSTOMER",
]


@asynccontextmanager
async def api_context(settings=SETTINGS):
    db = AsyncMongoMockClient(tz_aware=True).test
    await db.users.insert_one(dict(USER))
    actor = [USER]
    app = FastAPI()
    app.include_router(server.api_router)
    app.dependency_overrides[server.get_current_user] = lambda: actor[0]
    app.middleware("http")(server.trusted_origin)
    with patch.object(server, "db", db), patch.object(
        server.WhatsAppSettings, "from_env", return_value=settings
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app),
            base_url="http://test",
            headers={"Origin": "http://localhost:3000"},
        ) as browser:
            yield db, browser, actor


async def create(browser, opt_in=True):
    response = await browser.post(
        "/api/repairs",
        json={
            "whatsapp_opt_in": opt_in,
            "charger_info": {"brand": "ExampleBrand", "model": "AC 7.4 kW"},
            "problem_description": "Test power failure",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def setup_facts(browser, rid, status):
    if status == "ESTIMATE_SENT":
        response = await browser.patch(
            f"/api/repairs/{rid}/estimate",
            json={
                "parts": [{"name": "Test part", "qty": 1, "price": 2000}],
                "labor": 500,
                "tax": 250,
                "notes": "internal test marker",
            },
        )
        assert response.status_code == 200
    if status == "PAYMENT_PENDING":
        response = await browser.patch(
            f"/api/repairs/{rid}/payment",
            json={
                "amount_due": 1750,
                "reference": "Test reconciliation after confirmed receipts",
            },
        )
        assert response.status_code == 200
    if status == "SHIPPED_TO_CUSTOMER":
        response = await browser.patch(
            f"/api/repairs/{rid}/shipment",
            json={
                "leg": "return",
                "courier": "Example Courier",
                "tracking_number": "SAMPLE123456",
            },
        )
        assert response.status_code == 200


@pytest.mark.parametrize("opt_in", [True, False])
def test_eight_events_end_to_end_payloads_and_no_draft_notifications(opt_in):
    async def scenario():
        async with api_context() as (db, browser, actor):
            rid = await create(browser, opt_in)
            number = (await db.repair_requests.find_one({"id": rid}))[
                "repair_request_number"
            ]
            actor[0] = ADMIN
            for status in PATH:
                before = (await db.repair_requests.find_one({"id": rid}))[
                    "whatsapp_outbox"
                ]
                await setup_facts(browser, rid, status)
                assert (await db.repair_requests.find_one({"id": rid}))[
                    "whatsapp_outbox"
                ] == before
                response = await browser.patch(
                    f"/api/repairs/{rid}/status",
                    json={"status": status, "note": "private staff note"},
                )
                assert response.status_code == 200, response.text
                assert "whatsapp_outbox" not in response.json()
                assert "whatsapp_consent" not in response.json()
            stored = await db.repair_requests.find_one({"id": rid})
            assert [event["status"] for event in stored["whatsapp_outbox"]] == (
                SELECTED if opt_in else []
            )
            expected = {
                "REQUESTED": [USER["name"], number, "ExampleBrand AC 7.4 kW"],
                "AWAITING_SHIPMENT": [USER["name"], number, SETTINGS.dispatch_address],
                "RECEIVED_AT_VOLTX": [USER["name"], number],
                "ESTIMATE_SENT": [USER["name"], number, "2750.00"],
                "CUSTOMER_APPROVED": [USER["name"], number],
                "REPAIR_COMPLETED": [USER["name"], number],
                "PAYMENT_PENDING": [USER["name"], number, "1750.00"],
                "SHIPPED_TO_CUSTOMER": [
                    USER["name"],
                    number,
                    "Example Courier",
                    "SAMPLE123456",
                ],
            }
            calls = []

            def send(request):
                calls.append(json.loads(request.content))
                return httpx.Response(
                    200, json={"messages": [{"id": f"wamid.{len(calls)}"}]}
                )

            async with httpx.AsyncClient(transport=httpx.MockTransport(send)) as http:
                svc = WhatsAppService(db, SETTINGS, http)
                await svc.initialize()
                await asyncio.gather(svc.reconcile(), svc.reconcile())
                await asyncio.gather(*(svc.process_one() for _ in range(12)))
                assert len(calls) == (8 if opt_in else 0)
                for call in calls:
                    job = await db.whatsapp_jobs.find_one(
                        {"_id": call["biz_opaque_callback_data"]}
                    )
                    template = call["template"]
                    assert template["name"] == CATALOG[job["status"]]["name"]
                    assert template["language"]["code"] == "en_US"
                    assert [
                        p["text"] for p in template["components"][0]["parameters"]
                    ] == expected[job["status"]]
                    assert "private staff note" not in str(
                        call
                    ) and "internal test marker" not in str(call)
                    assert set(job["values"]) == set(
                        CATALOG[job["status"]]["parameters"]
                    )
                await svc.reconcile()
                assert not await svc.process_one()

    run(scenario)


@pytest.mark.parametrize(
    "target,current,facts",
    [
        ("ESTIMATE_SENT", "DIAGNOSING", {}),
        (
            "ESTIMATE_SENT",
            "DIAGNOSING",
            {"estimate": {"total": 900, "labor": 10, "status": "DRAFT"}},
        ),
        (
            "ESTIMATE_SENT",
            "DIAGNOSING",
            {"estimate": {"total": -1, "labor": -1, "status": "DRAFT"}},
        ),
        (
            "CUSTOMER_APPROVED",
            "ESTIMATE_SENT",
            {"estimate": {"total": 10, "labor": 10, "status": "DRAFT"}},
        ),
        ("PAYMENT_PENDING", "REPAIR_COMPLETED", {}),
        (
            "PAYMENT_PENDING",
            "REPAIR_COMPLETED",
            {"payment_summary": {"amount_due": 100}},
        ),
        ("SHIPPED_TO_CUSTOMER", "READY_TO_SHIP", {}),
        (
            "SHIPPED_TO_CUSTOMER",
            "READY_TO_SHIP",
            {"return_shipment": {"courier": "Example", "tracking_number": "Test"}},
        ),
    ],
)
def test_invalid_facts_reject_transition_without_history_or_outbox(
    target, current, facts
):
    async def scenario():
        async with api_context() as (db, browser, actor):
            rid = await create(browser)
            await db.repair_requests.update_one(
                {"id": rid}, {"$set": {"status": current, **facts}}
            )
            before = await db.repair_requests.find_one({"id": rid})
            actor[0] = ADMIN
            response = await browser.patch(
                f"/api/repairs/{rid}/status", json={"status": target}
            )
            assert response.status_code == 400
            assert await db.repair_requests.find_one({"id": rid}) == before

    run(scenario)


@pytest.mark.parametrize(
    "body",
    [
        {"labor": -1},
        {"parts": [{"name": "x", "price": -1}]},
        {"parts": [{"name": "x", "qty": 0}]},
        {"parts": [{"name": "x", "qty": 1.5}]},
    ],
)
def test_invalid_estimate_inputs_are_rejected(body):
    async def scenario():
        async with api_context() as (_, browser, actor):
            rid = await create(browser)
            actor[0] = ADMIN
            assert (
                await browser.patch(f"/api/repairs/{rid}/estimate", json=body)
            ).status_code == 422

    run(scenario)


def test_draft_edits_publish_freeze_and_payment_authority():
    async def scenario():
        async with api_context() as (db, browser, actor):
            rid = await create(browser)
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/payment",
                    json={"amount_due": 10, "reference": "test"},
                )
            ).status_code == 403
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/shipment",
                    json={"leg": "return", "courier": "X", "tracking_number": "T"},
                )
            ).status_code == 403
            actor[0] = ADMIN
            for status in PATH[:5]:
                await setup_facts(browser, rid, status)
                assert (
                    await browser.patch(
                        f"/api/repairs/{rid}/status", json={"status": status}
                    )
                ).status_code == 200
            assert (
                await browser.patch(f"/api/repairs/{rid}/estimate", json={"labor": 1})
            ).status_code == 409
            actor[0] = USER
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/status", json={"status": "CUSTOMER_APPROVED"}
                )
            ).status_code == 200
            actor[0] = ADMIN
            for status in ["REPAIRING", "REPAIR_COMPLETED"]:
                assert (
                    await browser.patch(
                        f"/api/repairs/{rid}/status", json={"status": status}
                    )
                ).status_code == 200
            await setup_facts(browser, rid, "PAYMENT_PENDING")
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/status", json={"status": "PAYMENT_PENDING"}
                )
            ).status_code == 200
            # A later confirmed payment invalidates a queued balance notice, with no invented payment URL.
            await browser.patch(
                f"/api/repairs/{rid}/payment",
                json={"amount_due": 0, "reference": "test paid in full"},
            )
            response = await browser.get(f"/api/repairs/{rid}")
            assert set(response.json()["payment_summary"]) == {
                "amount_due",
                "currency",
                "verified_at",
            }
            svc = WhatsAppService(db, SETTINGS)
            await svc.reconcile()
            await db.whatsapp_jobs.update_many(
                {"status": {"$ne": "PAYMENT_PENDING"}}, {"$set": {"state": "sent"}}
            )
            assert await svc.process_one()
            job = await db.whatsapp_jobs.find_one({"status": "PAYMENT_PENDING"})
            assert job["error_code"] == "business_facts_changed"

    run(scenario)


@pytest.mark.parametrize(
    "key,value",
    [
        ("approval_status", "pending"),
        ("approval_status", "rejected"),
        ("category", "MARKETING"),
        ("language", "en"),
        ("parameters", []),
        ("parameters", ["repair_number", "customer_name"]),
        ("parameters", {}),
        ("name", None),
        ("name", ""),
        ("name", "hello_world"),
    ],
)
def test_malformed_or_unapproved_templates_fail_closed(key, value):
    async def scenario():
        db, svc, _, calls, http = await fixture()
        templates = deepcopy(SETTINGS.templates)
        templates["REQUESTED"][key] = value
        svc.settings = replace(SETTINGS, templates=templates)
        async with http:
            await svc.process_one()
            assert not calls
            assert (await db.whatsapp_jobs.find_one({}))[
                "error_code"
            ] == "configuration_invalid"

    run(scenario)


def test_production_requires_manual_gate_all_eight_approvals_and_sender_isolation():
    production = replace(
        SETTINGS, mode="production", phone_number_id="99999", production_approved=True
    )
    validate_settings(production)
    for bad in [
        replace(production, production_approved=False),
        replace(production, phone_number_id=SETTINGS.test_phone_number_id),
        replace(SETTINGS, phone_number_id="99999"),
        replace(production, test_phone_number_id=""),
    ]:
        with pytest.raises(ConfigurationError):
            validate_settings(bad)
    for status in SELECTED:
        templates = deepcopy(SETTINGS.templates)
        templates.pop(status)
        with pytest.raises(ConfigurationError):
            validate_settings(replace(production, templates=templates))

    async def scenario():
        db, _, _, _, http = await fixture()
        await http.aclose()
        job = await db.whatsapp_jobs.find_one({})
        with pytest.raises(SnapshotError):
            message_payload(job, production)
        job.pop("schema_version")
        with pytest.raises(SnapshotError):
            message_payload(job, SETTINGS)

    run(scenario)


def test_withdrawal_is_authorized_idempotent_and_stops_pending_jobs():
    async def scenario():
        async with api_context() as (db, browser, actor):
            rid = await create(browser)
            actor[0] = {**USER, "user_id": "other"}
            assert (
                await browser.delete(f"/api/repairs/{rid}/whatsapp-consent")
            ).status_code == 403
            actor[0] = USER
            for _ in range(2):
                assert (
                    await browser.delete(f"/api/repairs/{rid}/whatsapp-consent")
                ).status_code == 200
            svc = WhatsAppService(db, SETTINGS)
            await svc.reconcile()
            assert await svc.process_one()
            assert (await db.whatsapp_jobs.find_one({}))[
                "error_code"
            ] == "consent_invalid"
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/status", json={"status": "AWAITING_SHIPMENT"}
                )
            ).status_code == 200
            assert (await db.repair_requests.find_one({"id": rid}))[
                "whatsapp_outbox"
            ] == []

    run(scenario)


@pytest.mark.parametrize(
    "error_cls", [httpx.ReadTimeout, httpx.WriteTimeout, httpx.RemoteProtocolError]
)
def test_ambiguous_transport_never_replays(error_cls):
    async def scenario():
        def fail(request):
            raise error_cls("sensitive request detail", request=request)

        db, svc, clock, calls, http = await fixture(fail)
        async with http:
            assert await svc.process_one()
            clock[0] += timedelta(days=1)
            assert not await svc.process_one()
            with pytest.raises(HTTPException) as error:
                await svc.safe_requeue("r1:REQUESTED")
            assert error.value.status_code == 409
            assert len(calls) == 1
            assert (await db.whatsapp_jobs.find_one({}))[
                "error_code"
            ] == "ambiguous_delivery"

    run(scenario)


def test_crash_after_acceptance_persistence_failure_cannot_duplicate():
    async def scenario():
        db, svc, clock, calls, http = await fixture()
        original = db.whatsapp_jobs.update_one

        async def fail_ack(query, update, **kwargs):
            if update.get("$set", {}).get("state") == "sent":
                raise RuntimeError("simulated DB interruption")
            return await original(query, update, **kwargs)

        async with http:
            with patch.object(db.whatsapp_jobs, "update_one", fail_ack):
                with pytest.raises(RuntimeError):
                    await svc.process_one()
            clock[0] += timedelta(seconds=121)
            assert await svc.process_one()
            assert len(calls) == 1
            assert (await db.whatsapp_jobs.find_one({}))[
                "error_code"
            ] == "ambiguous_delivery"

    run(scenario)


def test_connection_failure_retry_and_single_job_safe_replay():
    async def scenario():
        def fail(request):
            raise httpx.ConnectError("private detail", request=request)

        db, svc, clock, calls, http = await fixture(fail)
        async with http:
            await svc.process_one()
            job = await db.whatsapp_jobs.find_one({})
            assert (
                job["state"] == "retryable_failure" and not job["dispatch_started_at"]
            )
            await db.whatsapp_jobs.update_one({}, {"$set": {"state": "dead_letter"}})
            await svc.safe_requeue(job["_id"])
            with pytest.raises(HTTPException):
                await svc.safe_requeue(job["_id"])
            assert (await db.whatsapp_jobs.find_one({}))["manual_replays"] == 1
            assert len(calls) == 1  # Requeue has no provider side effect.

    run(scenario)


def test_shared_sender_throttle_blocks_other_jobs():
    async def scenario():
        db, svc, clock, calls, http = await fixture(
            lambda _: httpx.Response(429, headers={"Retry-After": "120"})
        )
        job = await db.whatsapp_jobs.find_one({})
        await db.whatsapp_jobs.insert_one({**job, "_id": "other-event"})
        async with http:
            await svc.process_one()
            assert not await svc.process_one()
            assert len(calls) == 1
            clock[0] += timedelta(seconds=120)
            assert await svc.process_one()

    run(scenario)


def test_metrics_redacted_and_admin_endpoints_protected():
    async def scenario():
        db, svc, clock, _, http = await fixture()
        await http.aclose()
        clock[0] += timedelta(seconds=301)
        await db.whatsapp_jobs.update_one(
            {},
            {"$set": {"state": "dead_letter", "error_code": "configuration_invalid"}},
        )
        metrics = await svc.metrics()
        assert (
            metrics["alerts"]["dead_letters"]
            and metrics["alerts"]["invalid_configuration"]
        )
        for secret in [
            USER["name"],
            PHONE,
            SETTINGS.access_token,
            SETTINGS.dispatch_address,
        ]:
            assert secret not in json.dumps(metrics)
        async with api_context() as (_, browser, actor):
            assert (await browser.get("/api/admin/whatsapp/metrics")).status_code == 403
            assert (
                await browser.post("/api/admin/whatsapp/jobs/test/retry")
            ).status_code == 403
            actor[0] = ADMIN
            assert (await browser.get("/api/admin/whatsapp/metrics")).status_code == 200

    run(scenario)


def test_webhook_limits_malformed_payload_sender_scope_and_disabled_config():
    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).test
        app = FastAPI()
        app.include_router(webhook_router(lambda: db, lambda: SETTINGS))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as browser:

            async def post(raw):
                signature = (
                    "sha256="
                    + hmac.new(
                        SETTINGS.app_secret.encode(), raw, hashlib.sha256
                    ).hexdigest()
                )
                return await browser.post(
                    "/webhooks/whatsapp",
                    content=raw,
                    headers={"X-Hub-Signature-256": signature},
                )

            assert (await post(b"[")).status_code == 400
            assert (await post(b"x" * (1024 * 1024 + 1))).status_code == 413
            payload = receipt_payload()
            value = payload["entry"][0]["changes"][0]["value"]
            value["metadata"]["phone_number_id"] = "other-sender"
            assert (await post(json.dumps(payload).encode())).status_code == 200
            assert await db.whatsapp_receipts.count_documents({}) == 0
            value["metadata"]["phone_number_id"] = SETTINGS.phone_number_id
            value["statuses"] *= 101
            assert (await post(json.dumps(payload).encode())).status_code == 413
            assert await db.whatsapp_receipts.count_documents({}) == 0

    run(scenario)


@pytest.mark.parametrize(
    "target,current,facts,mutate",
    [
        (
            "ESTIMATE_SENT",
            "DIAGNOSING",
            {"estimate": {"status": "DRAFT", "labor": 10, "total": 10}},
            {"estimate": {"status": "DRAFT", "labor": 20, "total": 20}},
        ),
        (
            "PAYMENT_PENDING",
            "REPAIR_COMPLETED",
            {
                "payment_summary": {
                    "amount_due": 10,
                    "currency": "INR",
                    "source": "manual_reconciliation",
                    "verified_at": "test",
                    "verified_by": "admin",
                }
            },
            {"payment_summary.amount_due": 0},
        ),
        (
            "SHIPPED_TO_CUSTOMER",
            "READY_TO_SHIP",
            {
                "return_shipment": {
                    "courier": "Example",
                    "tracking_number": "A",
                    "confirmed_at": "test",
                    "confirmed_by": "admin",
                }
            },
            {"return_shipment.tracking_number": "B"},
        ),
    ],
)
def test_fact_edit_racing_transition_returns_conflict_without_event(
    target, current, facts, mutate
):
    async def scenario():
        async with api_context() as (db, browser, actor):
            rid = await create(browser)
            await db.repair_requests.update_one(
                {"id": rid}, {"$set": {"status": current, **facts}}
            )
            collection = db.repair_requests
            original = collection.update_one
            stable = SimpleNamespace(repair_requests=collection, users=db.users)

            async def race(query, update, **kwargs):
                if update.get("$set", {}).get("status") == target:
                    await original(
                        {"id": rid}, {"$set": mutate, "$inc": {"revision": 1}}
                    )
                return await original(query, update, **kwargs)

            with patch.object(server, "db", stable), patch.object(
                collection, "update_one", race
            ):
                with pytest.raises(HTTPException) as error:
                    await server.update_repair_status(
                        rid, server.RepairStatusUpdate(status=target), ADMIN
                    )
            assert error.value.status_code == 409
            repair = await collection.find_one({"id": rid})
            assert repair["status"] == current
            assert [e["status"] for e in repair["whatsapp_outbox"]] == ["REQUESTED"]

    run(scenario)


@pytest.mark.parametrize("branch", ["CUSTOMER_DECLINED", "NOT_REPAIRABLE", "CANCELLED"])
def test_alternate_branches_preserved_and_nonselected_statuses_silent(branch):
    async def scenario():
        async with api_context() as (db, browser, actor):
            rid = await create(browser)
            actor[0] = ADMIN
            for status in PATH[:4]:
                assert (
                    await browser.patch(
                        f"/api/repairs/{rid}/status", json={"status": status}
                    )
                ).status_code == 200
            if branch == "CUSTOMER_DECLINED":
                await setup_facts(browser, rid, "ESTIMATE_SENT")
                assert (
                    await browser.patch(
                        f"/api/repairs/{rid}/status", json={"status": "ESTIMATE_SENT"}
                    )
                ).status_code == 200
            before = (await db.repair_requests.find_one({"id": rid}))["whatsapp_outbox"]
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/status", json={"status": branch}
                )
            ).status_code == 200
            assert (await db.repair_requests.find_one({"id": rid}))[
                "whatsapp_outbox"
            ] == before
            if branch != "CANCELLED":
                assert (
                    await browser.patch(
                        f"/api/repairs/{rid}/status", json={"status": "READY_TO_SHIP"}
                    )
                ).status_code == 200
            for target in ["REQUESTED", "ESTIMATE_APPROVED", "RETURN_SHIPPED"]:
                assert (
                    await browser.patch(
                        f"/api/repairs/{rid}/status", json={"status": target}
                    )
                ).status_code == 400

    run(scenario)


@pytest.mark.parametrize("value", ["", "  ", None, "line\nbreak"])
def test_missing_personalization_never_sends(value):
    async def scenario():
        db, svc, _, calls, http = await fixture()
        await db.whatsapp_jobs.update_one({}, {"$set": {"values.customer_name": value}})
        async with http:
            await svc.process_one()
            assert not calls
            assert (await db.whatsapp_jobs.find_one({}))[
                "error_code"
            ] == "snapshot_invalid"

    run(scenario)


def test_missing_dispatch_address_blocks_notice_without_blocking_repair():
    async def scenario():
        async with api_context(replace(SETTINGS, dispatch_address="")) as (
            db,
            browser,
            actor,
        ):
            rid = await create(browser)
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/status", json={"status": "AWAITING_SHIPMENT"}
                )
            ).status_code == 200
            svc = WhatsAppService(db, SETTINGS)
            await svc.reconcile()
            await db.whatsapp_jobs.update_one(
                {"status": "REQUESTED"}, {"$set": {"state": "sent"}}
            )
            await svc.process_one()
            assert (await db.whatsapp_jobs.find_one({"status": "AWAITING_SHIPMENT"}))[
                "error_code"
            ] == "snapshot_invalid"

    run(scenario)


def test_catalog_consistency_and_unknown_approvals():
    import re

    assert set(CATALOG) == set(SELECTED) | {"PAYMENT_RECEIVED"}
    for spec in CATALOG.values():
        assert spec["language"] == "en_US" and spec["category"] == "UTILITY"
        assert re.findall(r"\{\{(\d+)\}\}", spec["body"]) == [
            str(i + 1) for i in range(len(spec["parameters"]))
        ]
        assert len(spec["examples"]) == len(spec["parameters"])
        assert all(
            spec[key] == "unknown"
            for key in ("configured", "submitted", "approved", "pending", "blocked")
        )


def test_disabled_feature_records_consent_but_no_events():
    async def scenario():
        async with api_context(replace(SETTINGS, enabled=False)) as (db, browser, _):
            rid = await create(browser)
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/status", json={"status": "AWAITING_SHIPMENT"}
                )
            ).status_code == 200
            repair = await db.repair_requests.find_one({"id": rid})
            assert repair["whatsapp_consent"]["opted_in"] is True
            assert repair["whatsapp_outbox"] == []

    run(scenario)


@pytest.mark.parametrize(
    "path",
    [
        "/api/webhooks/whatsapp/?hub.verify_token=private",
        "/other?%68ub.verify_token=private",
    ],
)
def test_redirect_and_encoded_verification_tokens_not_logged(path):
    import logging
    from services.whatsapp_service import WebhookAccessLogFilter

    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        1,
        "%s %s %s %s %s",
        ("client", "GET", path, "1.1", 307),
        None,
    )
    assert WebhookAccessLogFilter().filter(record)
    assert "private" not in record.getMessage()
