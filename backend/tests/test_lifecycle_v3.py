"""Lifecycle v3 contracts on disposable databases and mocked provider HTTP only."""

import asyncio
import json
import os
import secrets
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace, MethodType

import httpx
import pytest
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient
from motor.motor_asyncio import AsyncIOMotorClient
from urllib.parse import urlsplit

from auth_service import AuthService, AuthSettings
from services.lifecycle_policy import (
    LifecyclePolicy,
    digest,
    preference,
    instruction_preview,
)
from services.payment_repository import MongoPaymentRepository
from services.payment_service import PaymentService, ManualPaymentProcessor
from services.whatsapp_service import (
    Settings,
    SnapshotError,
    ConfigurationError,
    WhatsAppService,
    LIFECYCLE_CATALOG,
    message_payload,
    validate_settings,
)
from test_whatsapp import SETTINGS, USER

VERIFIED = {
    **USER,
    "phone_verified_at": "2026-11-20T00:00:00+00:00",
    "phone_generation": 0,
}
TEMPLATES = {
    key: {
        "name": item["name"],
        "language": item["language"],
        "category": "UTILITY",
        "parameters": item["parameters"],
        "approval_status": "approved",
    }
    for key, item in LIFECYCLE_CATALOG.items()
}
ACTIVE = replace(
    SETTINGS, activation_id="00000000-0000-4000-8000-000000000042", templates=TEMPLATES
)


async def fixture(db, settings=ACTIVE, status="REQUESTED"):
    policy = LifecyclePolicy(db, settings)
    await db.users.insert_one(dict(VERIFIED))
    await db.whatsapp_control.insert_one(
        {
            "_id": policy.scope_id(),
            "activation_id": settings.activation_id,
            "paused": False,
            "mode": settings.mode,
            "manifest_digest": digest(settings.templates),
            "instructions_digest": digest(instruction_preview(settings)),
            "heartbeat_at": datetime.now(timezone.utc),
        }
    )
    repair = {
        "id": "repair",
        "repair_request_number": "TEST-10421",
        "user_id": USER["user_id"],
        "status": status,
        "revision": 0,
        "charger_info": {"brand": "Test charger"},
        "whatsapp_consent": {
            "opted_in": True,
            "version": 2,
            "revision": 0,
            "source": "repair_submission_v2",
            "scope_id": policy.scope_id(),
            "destination": USER["phone"],
            "phone_generation": 0,
            "activation_id": settings.activation_id,
            "at": datetime.now(timezone.utc).isoformat(),
        },
        "whatsapp_outbox": [],
    }
    await db.repair_requests.insert_one(deepcopy(repair))
    return policy, repair


def validate_local_uri(uri):
    parsed = urlsplit(uri)
    assert parsed.scheme == "mongodb"
    assert parsed.hostname in ("127.0.0.1", "localhost", "::1")
    assert parsed.port and "," not in parsed.netloc and "@" not in parsed.netloc
    assert not parsed.query and not parsed.fragment


def run(scenario, real=False):
    async def execute():
        if real:
            uri = os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017")
            validate_local_uri(uri)
            client = AsyncIOMotorClient(
                uri, tz_aware=True, serverSelectionTimeoutMS=3000, directConnection=True
            )
        else:
            client = AsyncMongoMockClient(tz_aware=True)
        name = "voltx_lifecycle_test_" + secrets.token_hex(8)
        try:
            await scenario(client[name])
        finally:
            await client.drop_database(name)
            if real:
                client.close()

    asyncio.run(execute())


def test_runtime_old_configuration_cannot_enable_legacy_sending(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ENABLED", "true")
    monkeypatch.delenv("WHATSAPP_LIFECYCLE_ENABLED", raising=False)
    monkeypatch.delenv("WHATSAPP_LIFECYCLE_ACTIVATION_ID", raising=False)
    assert not Settings.from_env().enabled
    monkeypatch.setenv("WHATSAPP_LIFECYCLE_ENABLED", "true")
    assert not Settings.from_env().enabled
    monkeypatch.setenv("WHATSAPP_LIFECYCLE_ACTIVATION_ID", "test-scope")
    assert Settings.from_env().enabled


def test_eight_milestones_have_nine_mutually_exclusive_template_variants():
    keys = set(LIFECYCLE_CATALOG)
    assert len(keys) == 9
    assert "CUSTOMER_APPROVED" in keys and "PAYMENT_RECEIVED" in keys
    assert not keys.intersection({"REPAIR_COMPLETED", "PAYMENT_PENDING"})
    assert keys.intersection({"REPAIR_RESULT_DUE", "REPAIR_RESULT_CLEAR"}) == {
        "REPAIR_RESULT_DUE",
        "REPAIR_RESULT_CLEAR",
    }
    validate_settings(ACTIVE)


@pytest.mark.parametrize(
    "amount,key", [("2750.00", "REPAIR_RESULT_DUE"), ("0.00", "REPAIR_RESULT_CLEAR")]
)
def test_combined_snapshot_and_exact_payload(amount, key):
    async def scenario(db):
        policy, repair = await fixture(db, status="REPAIR_COMPLETED")
        repair["payment_summary"] = {
            "amount_due": amount,
            "currency": "INR",
            "balance_state": "BALANCE_VERIFIED",
            "verified_at": "test",
            "verified_by": "admin",
        }
        job = await policy.event(repair, "REPAIR_RESULT", "arbitrary-save-key")
        assert job["_id"] == "repair:REPAIR_RESULT"
        assert job["template_key"] == key
        payload = message_payload(job, ACTIVE)
        assert payload["template"]["name"] == LIFECYCLE_CATALOG[key]["name"]
        assert len(payload["template"]["components"][0]["parameters"]) == (
            3 if amount != "0.00" else 2
        )
        assert ("amount_due" in job["values"]) == (amount != "0.00")
        assert await policy.event(repair, "REPAIR_COMPLETED", "old") is None
        assert await policy.event(repair, "PAYMENT_PENDING", "old") is None

    run(scenario)


def test_unknown_balance_is_not_a_zero_balance():
    async def scenario(db):
        policy, repair = await fixture(db, status="REPAIR_COMPLETED")
        with pytest.raises(HTTPException):
            await policy.event(repair, "REPAIR_RESULT", "result")

    run(scenario)


@pytest.mark.parametrize("real", [False, True])
@pytest.mark.parametrize("amount", ["2750.00", "0.00"])
def test_concurrent_balance_attestations_reserve_exactly_one_result(real, amount):
    async def scenario(db):
        policy, repair = await fixture(db, status="REPAIR_COMPLETED")
        service = PaymentService(
            MongoPaymentRepository(db.repair_requests, db.payment_references),
            ManualPaymentProcessor(),
            balance_notification_factory=lambda r: policy.event(
                r, "REPAIR_RESULT", "result"
            ),
        )
        await asyncio.gather(
            *(
                service.verify_balance(
                    "repair", amount, "test-reconciliation", "admin", "same-request"
                )
                for _ in range(5)
            )
        )
        stored = await db.repair_requests.find_one({"id": "repair"})
        assert len(stored["whatsapp_outbox"]) == 1
        assert stored["completion_notice"]["event_id"] == "repair:REPAIR_RESULT"
        assert len(stored["payment_records"]) == 1
        assert not stored.get("payment_receipt")
        first = deepcopy(stored["whatsapp_outbox"][0])
        await service.verify_balance(
            "repair", "100.00", "updated-reconciliation", "admin", "later-request"
        )
        stored = await db.repair_requests.find_one({"id": "repair"})
        assert stored["whatsapp_outbox"] == [first]
        assert await policy.reject_reason(first) == "business_facts_changed"

    run(scenario, real=real)


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"whatsapp_consent.opted_in": False}, "consent_withdrawn"),
        ({"whatsapp_consent.revision": 1}, "consent_withdrawn"),
        ({"status": "DIAGNOSING"}, "event_superseded"),
        ({"whatsapp_consent.activation_id": "old"}, "phone_changed"),
    ],
)
def test_current_consent_and_status_rechecked(change, expected):
    async def scenario(db):
        policy, repair = await fixture(db)
        job = await policy.event(repair, "REQUESTED", "initial")
        assert await policy.reject_reason(job) is None
        await db.repair_requests.update_one({"id": "repair"}, {"$set": change})
        assert await policy.reject_reason(job) == expected

    run(scenario)


def test_phone_change_away_and_back_cannot_revive_consent():
    async def scenario(db):
        policy, repair = await fixture(db)
        job = await policy.event(repair, "REQUESTED", "initial")
        await db.users.update_one(
            {"user_id": USER["user_id"]}, {"$set": {"phone_generation": 2}}
        )
        assert await policy.reject_reason(job) == "phone_changed"
        assert (
            preference(repair, {**VERIFIED, "phone_generation": 2})["state"]
            == "paused_phone_change"
        )

    run(scenario)


def test_capability_binding_is_purpose_session_and_identity_bound():
    async def scenario(db):
        policy, repair = await fixture(db)
        auth = SimpleNamespace(
            settings=AuthSettings(
                "test-only-secret-at-least-thirty-two-characters", "test", "demo", True
            ),
            session_id=lambda request: request["session"],
        )
        auth.decode = MethodType(AuthService.decode, auth)
        cap = await policy.capability(VERIFIED, auth, {"session": "first"})
        assert cap["available"] and cap["binding"]
        good = await policy.consent(
            True, cap["binding"], VERIFIED, auth, {"session": "first"}
        )
        assert good["version"] == 2 and good["activation_id"] == ACTIVE.activation_id
        for user, session in [
            (VERIFIED, "other"),
            ({**VERIFIED, "phone_generation": 1}, "first"),
        ]:
            with pytest.raises(HTTPException) as exc:
                await policy.consent(
                    True, cap["binding"], user, auth, {"session": session}
                )
            assert exc.value.status_code == 409
        await db.whatsapp_control.update_one(
            {"_id": policy.scope_id()}, {"$set": {"paused": True}}
        )
        assert not (await policy.capability(VERIFIED, auth, {"session": "first"}))[
            "available"
        ]
        assert (
            await policy.consent(
                True, cap["binding"], VERIFIED, auth, {"session": "first"}
            )
        )["activation_id"] is None

    run(scenario)


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"schema_version": 2}, "legacy_snapshot"),
        ({"activation_id": "old"}, "activation_mismatch"),
        (
            {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)},
            "event_expired",
        ),
    ],
)
def test_legacy_scope_and_expiry_block_dispatch(change, expected):
    async def scenario(db):
        policy, repair = await fixture(db)
        job = {**await policy.event(repair, "REQUESTED", "initial"), **change}
        assert await policy.reject_reason(job) == expected

    run(scenario)


def test_worker_accepts_one_message_and_rechecks_withdrawal_after_intent():
    async def scenario(db):
        policy, repair = await fixture(db)
        job = await policy.event(repair, "REQUESTED", "initial")
        await db.repair_requests.update_one(
            {"id": "repair"}, {"$push": {"whatsapp_outbox": job}}
        )
        calls = []

        async def transport(request):
            calls.append(json.loads(request.content))
            return httpx.Response(200, json={"messages": [{"id": "test-message"}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
            worker = WhatsAppService(db, ACTIVE, http)
            await worker.reconcile()
            assert await worker.process_one()
            assert not await worker.process_one()
        assert len(calls) == 1
        assert (await db.whatsapp_jobs.find_one({}))["state"] == "sent"

    run(scenario)


def test_unsent_result_with_later_receipt_is_suppressed_without_replacement():
    async def scenario(db):
        policy, repair = await fixture(db, status="REPAIR_COMPLETED")
        repair["payment_summary"] = {
            "amount_due": "100.00",
            "currency": "INR",
            "balance_state": "BALANCE_VERIFIED",
            "verified_at": "one",
            "verified_by": "admin",
        }
        await db.repair_requests.update_one(
            {"id": "repair"}, {"$set": {"payment_summary": repair["payment_summary"]}}
        )
        job = await policy.event(repair, "REPAIR_RESULT", "result")
        await db.repair_requests.update_one(
            {"id": "repair"}, {"$set": {"payment_summary.amount_due": 0}}
        )
        assert await policy.reject_reason(job) == "business_facts_changed"
        assert (
            message_payload(job, ACTIVE)["template"]["name"]
            == LIFECYCLE_CATALOG["REPAIR_RESULT_DUE"]["name"]
        )

    run(scenario)


def test_api_v3_capability_creation_idempotency_and_team_acceptance():
    from unittest.mock import patch
    from test_customer_profile import run as profile_run, sign_in
    import server

    async def scenario(auth, db, browser, clock):
        user = await sign_in(
            auth, db, browser, uid=USER["user_id"], phone=USER["phone"]
        )
        policy = LifecyclePolicy(db, ACTIVE)
        await db.whatsapp_control.insert_one(
            {
                "_id": policy.scope_id(),
                "activation_id": ACTIVE.activation_id,
                "paused": False,
                "mode": ACTIVE.mode,
                "manifest_digest": digest(ACTIVE.templates),
                "instructions_digest": digest(instruction_preview(ACTIVE)),
                "heartbeat_at": datetime.now(timezone.utc),
            }
        )
        with patch.object(server.WhatsAppSettings, "from_env", return_value=ACTIVE):
            cap = (await browser.get("/api/customer/whatsapp-capability")).json()
            assert cap["available"]
            body = {
                "charger_info": {"brand": "Test charger"},
                "problem_description": "Synthetic fault",
                "whatsapp_opt_in": True,
                "whatsapp_binding": cap["binding"],
                "idempotency_key": "creation-test",
            }
            response = await browser.post("/api/repairs", json=body)
            assert response.status_code == 200, response.text
            repair = response.json()
            assert (
                repair["status"] == "REQUESTED"
                and repair["whatsapp_updates"]["state"] == "enabled"
            )
            rid = repair["id"]
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/status", json={"status": "AWAITING_SHIPMENT"}
                )
            ).status_code == 403
            await db.users.update_one(
                {"user_id": user["user_id"]}, {"$set": {"phone_generation": 1}}
            )
            retry = await browser.post("/api/repairs", json=body)
            assert retry.status_code == 200 and retry.json()["id"] == rid
            body["idempotency_key"] = "different-request"
            assert (await browser.post("/api/repairs", json=body)).status_code == 409
            assert await db.repair_requests.count_documents({}) == 1
            await sign_in(
                auth, db, browser, uid="admin", phone="+919000000001", role="admin"
            )
            preview = (await browser.get(f"/api/repairs/{rid}")).json()[
                "intake_preview"
            ]
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/status", json={"status": "AWAITING_SHIPMENT"}
                )
            ).status_code == 409
            stale = await browser.patch(
                f"/api/repairs/{rid}/status",
                json={
                    "status": "AWAITING_SHIPMENT",
                    "acceptance": {"confirmed": True, "preview_digest": "0" * 64},
                },
            )
            assert stale.status_code == 409
            assert (await db.repair_requests.find_one({"id": rid}))[
                "status"
            ] == "REQUESTED"
            accept = {
                "status": "AWAITING_SHIPMENT",
                "acceptance": {"confirmed": True, "preview_digest": preview["digest"]},
            }
            assert (
                await browser.patch(f"/api/repairs/{rid}/status", json=accept)
            ).status_code == 200
            assert (
                await browser.patch(f"/api/repairs/{rid}/status", json=accept)
            ).status_code == 200
            stored = await db.repair_requests.find_one({"id": rid})
            assert (
                len(stored["status_history"]) == 2
                and stored["intake_acceptance"]["by"] == "admin"
            )
            # Old phone generation cannot enqueue new instructions or receive a queued notice.
            assert len(stored["whatsapp_outbox"]) == 1

    profile_run(scenario)


def test_withdrawal_winning_final_check_prevents_http_even_after_intent():
    from unittest.mock import patch

    async def scenario(db):
        policy, repair = await fixture(db)
        job = await policy.event(repair, "REQUESTED", "initial")
        await db.repair_requests.update_one(
            {"id": "repair"}, {"$push": {"whatsapp_outbox": job}}
        )
        checks = 0
        original = LifecyclePolicy.reject_reason

        async def revoke_before_final_check(self, current):
            nonlocal checks
            checks += 1
            if checks == 2:
                await db.repair_requests.update_one(
                    {"id": "repair"}, {"$set": {"whatsapp_consent.opted_in": False}}
                )
            return await original(self, current)

        calls = []

        async def transport(request):
            calls.append(request)
            return httpx.Response(200, json={"messages": [{"id": "must-not-send"}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
            worker = WhatsAppService(db, ACTIVE, http)
            await worker.reconcile()
            with patch.object(
                LifecyclePolicy, "reject_reason", revoke_before_final_check
            ):
                assert await worker.process_one()
        stored = await db.whatsapp_jobs.find_one({})
        assert (
            not calls
            and stored["state"] == "suppressed"
            and stored["error_code"] == "consent_withdrawn"
        )
        # A persisted intent is never erased to enable an unsafe replay.
        assert stored["dispatch_started_at"]
        with pytest.raises(HTTPException):
            await worker.safe_requeue(stored["_id"])

    run(scenario)


def test_readiness_is_read_only_and_requires_all_reviewed_indexes():
    from services.lifecycle_readiness import report, INDEX_PLAN

    async def scenario(db):
        policy, _ = await fixture(db)
        first = await report(db, ACTIVE)
        assert first["ready"] is False and first["reason"] == "indexes_require_review"
        assert await db.whatsapp_jobs.index_information() == {}
        # Explicit test-only installation into a disposable database.
        for collection, plans in INDEX_PLAN.items():
            for keys, options in plans:
                await db[collection].create_index(keys, **options)
        assert (await report(db, ACTIVE))["ready"] is True
        await db.whatsapp_control.update_one(
            {"_id": policy.scope_id()}, {"$set": {"paused": True}}
        )
        assert not (await report(db, ACTIVE))["ready"]

    run(scenario)


def test_all_eight_v3_messages_follow_real_api_milestones_with_mock_transport():
    from unittest.mock import patch
    from test_customer_profile import run as profile_run, sign_in
    import server

    async def scenario(auth, db, browser, clock):
        await sign_in(auth, db, browser, uid=USER["user_id"], phone=USER["phone"])
        policy = LifecyclePolicy(db, ACTIVE)
        await db.whatsapp_control.insert_one(
            {
                "_id": policy.scope_id(),
                "activation_id": ACTIVE.activation_id,
                "paused": False,
                "mode": ACTIVE.mode,
                "manifest_digest": digest(ACTIVE.templates),
                "instructions_digest": digest(instruction_preview(ACTIVE)),
                "heartbeat_at": datetime.now(timezone.utc),
            }
        )
        sent = []

        async def transport(request):
            sent.append(json.loads(request.content)["template"]["name"])
            return httpx.Response(
                200, json={"messages": [{"id": f"synthetic-{len(sent)}"}]}
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
            worker = WhatsAppService(db, ACTIVE, http)

            async def flush():
                await worker.reconcile()
                for _ in range(12):
                    if not await worker.process_one():
                        break

            with patch.object(server.WhatsAppSettings, "from_env", return_value=ACTIVE):
                cap = (await browser.get("/api/customer/whatsapp-capability")).json()
                created = await browser.post(
                    "/api/repairs",
                    json={
                        "charger_info": {"brand": "Synthetic brand"},
                        "problem_description": "Synthetic fault",
                        "whatsapp_opt_in": True,
                        "whatsapp_binding": cap["binding"],
                        "idempotency_key": "journey",
                    },
                )
                assert created.status_code == 200, created.text
                rid = created.json()["id"]

                async def status(target, **extra):
                    response = await browser.patch(
                        f"/api/repairs/{rid}/status", json={"status": target, **extra}
                    )
                    assert response.status_code == 200, response.text
                    await flush()

                await flush()
                await sign_in(
                    auth, db, browser, uid="admin", phone="+919000000001", role="admin"
                )
                preview = (await browser.get(f"/api/repairs/{rid}")).json()[
                    "intake_preview"
                ]
                await status(
                    "AWAITING_SHIPMENT",
                    acceptance={"confirmed": True, "preview_digest": preview["digest"]},
                )
                await status("IN_TRANSIT_TO_VOLTX")
                await status("RECEIVED_AT_VOLTX")
                await status("DIAGNOSING")
                assert (
                    await browser.patch(
                        f"/api/repairs/{rid}/estimate", json={"labor": 100}
                    )
                ).status_code == 200
                await status("ESTIMATE_SENT")
                await sign_in(
                    auth, db, browser, uid=USER["user_id"], phone=USER["phone"]
                )
                await status("CUSTOMER_APPROVED")
                await sign_in(
                    auth, db, browser, uid="admin", phone="+919000000001", role="admin"
                )
                await status("REPAIRING")
                await status("REPAIR_COMPLETED")
                assert len(sent) == 5  # Completion alone must never notify.
                balance = {
                    "amount_due": 100,
                    "reference": "Synthetic reconciliation",
                    "idempotency_key": "balance",
                }
                assert (
                    await browser.patch(f"/api/repairs/{rid}/payment", json=balance)
                ).status_code == 200
                await flush()
                assert (
                    await browser.patch(f"/api/repairs/{rid}/payment", json=balance)
                ).status_code == 200
                await status("PAYMENT_PENDING")
                assert len(sent) == 6
                receipt = await browser.post(
                    f"/api/repairs/{rid}/payment/verify",
                    json={
                        "amount": 100,
                        "method": "cash",
                        "idempotency_key": "receipt",
                        "funds_received": True,
                    },
                )
                assert receipt.status_code == 200, receipt.text
                await flush()
                await status("READY_TO_SHIP")
                shipment = await browser.patch(
                    f"/api/repairs/{rid}/shipment",
                    json={
                        "leg": "return",
                        "courier": "Synthetic Courier",
                        "tracking_number": "TEST-TRACKING",
                    },
                )
                assert shipment.status_code == 200, shipment.text
                await status("SHIPPED_TO_CUSTOMER")
                expected = [
                    "REQUESTED",
                    "AWAITING_SHIPMENT",
                    "RECEIVED_AT_VOLTX",
                    "ESTIMATE_SENT",
                    "CUSTOMER_APPROVED",
                    "REPAIR_RESULT_DUE",
                    "PAYMENT_RECEIVED",
                    "SHIPPED_TO_CUSTOMER",
                ]
                assert sent == [LIFECYCLE_CATALOG[key]["name"] for key in expected]
                assert await db.whatsapp_jobs.count_documents({"state": "sent"}) == 8
                assert not await worker.process_one()

    profile_run(scenario)


def test_control_changes_require_confirmation_and_paused_verified_scope():
    from services.lifecycle_control import change
    from services.lifecycle_readiness import INDEX_PLAN

    async def scenario(db):
        policy, _ = await fixture(db)
        for collection, plans in INDEX_PLAN.items():
            for keys, options in plans:
                await db[collection].create_index(keys, **options)
        with pytest.raises(ValueError):
            await change(db, ACTIVE, "pause")
        await change(db, ACTIVE, "pause", reviewed=True)
        assert await policy.scope() is None
        await change(db, ACTIVE, "resume", reviewed=True)
        assert await policy.scope()
        newer = replace(ACTIVE, activation_id="00000000-0000-4000-8000-000000000043")
        with pytest.raises(ValueError):
            await change(db, newer, "activate", reviewed=True)
        await change(db, ACTIVE, "pause", reviewed=True)
        await change(db, newer, "activate", reviewed=True)
        assert not await policy.scope()
        assert await LifecyclePolicy(db, newer).scope()
        scope = await db.whatsapp_control.find_one({"_id": policy.scope_id()})
        assert (
            scope["heartbeat_at"] is None
        )  # Activation does not impersonate a worker.

    run(scenario)


@pytest.mark.parametrize("test_sender_id", [ACTIVE.test_phone_number_id, ""])
def test_staging_window_expiry_fails_closed_with_matching_sender_and_allowlist(
    monkeypatch,
    test_sender_id,
):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv(
        "MONGO_URL",
        "mongodb+srv://rushx_staging_app:synthetic@voltx-staging.ovofwvn.mongodb.net",
    )
    monkeypatch.setenv("DB_NAME", "rushx_staging")
    monkeypatch.setenv("OTP_MODE", "provider")
    monkeypatch.setenv("EXPOSE_DEMO_OTP", "false")
    monkeypatch.setenv("CORS_ORIGINS", "https://staging.evchargerrepair.in")
    monkeypatch.setenv("WHATSAPP_ENABLED", "false")
    # No real connection is made; the scope checks run on a mock DB.
    staged = replace(
        ACTIVE,
        mode="staging",
        test_phone_number_id=test_sender_id,
        production_approved=False,
        staging_enabled=True,
        staging_sender=ACTIVE.phone_number_id,
        staging_recipients=(USER["phone"],),
    )

    async def scenario(db):
        policy, _ = await fixture(db, staged)
        assert not await policy.scope()  # A window is mandatory.
        await db.whatsapp_control.update_one(
            {"_id": policy.scope_id()},
            {
                "$set": {
                    "test_until": datetime.now(timezone.utc) + timedelta(minutes=10)
                }
            },
        )
        assert await policy.scope()
        await db.whatsapp_control.update_one(
            {"_id": policy.scope_id()},
            {"$set": {"test_until": datetime.now(timezone.utc) - timedelta(seconds=1)}},
        )
        assert not await policy.scope()

    run(scenario)


def test_explicit_continuous_staging_scope_does_not_require_expiry(monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv(
        "MONGO_URL",
        "mongodb+srv://rushx_staging_app:synthetic@voltx-staging.ovofwvn.mongodb.net",
    )
    monkeypatch.setenv("DB_NAME", "rushx_staging")
    monkeypatch.setenv("OTP_MODE", "provider")
    monkeypatch.setenv("EXPOSE_DEMO_OTP", "false")
    monkeypatch.setenv("CORS_ORIGINS", "https://staging.evchargerrepair.in")
    monkeypatch.setenv("WHATSAPP_ENABLED", "false")
    staged = replace(
        ACTIVE,
        mode="staging",
        production_approved=False,
        staging_enabled=True,
        staging_continuous=True,
        staging_sender=ACTIVE.phone_number_id,
        staging_recipients=(USER["phone"],),
    )

    async def scenario(db):
        policy, _ = await fixture(db, staged)
        await db.whatsapp_control.update_one(
            {"_id": policy.scope_id()},
            {"$set": {"continuous": True, "test_until": None}},
        )
        assert await policy.scope()
        await db.whatsapp_control.update_one(
            {"_id": policy.scope_id()}, {"$set": {"continuous": False}}
        )
        assert not await policy.scope()
        await db.whatsapp_control.update_one(
            {"_id": policy.scope_id()},
            {
                "$set": {
                    "continuous": False,
                    "test_until": datetime.now(timezone.utc) + timedelta(minutes=10),
                }
            },
        )
        assert await policy.scope()

    run(scenario)


@pytest.mark.parametrize("real", [False, True])
def test_per_repair_dispatch_fence_orders_receipt_before_return_notice(real):
    async def scenario(db):
        policy, repair = await fixture(db, status="SHIPPED_TO_CUSTOMER")
        repair.update(
            payment_receipt={"id": "receipt"},
            return_shipment={
                "courier": "Synthetic Courier",
                "tracking_number": "TEST-TRACKING",
                "confirmed_by": "admin",
                "confirmed_at": "test",
            },
        )
        receipt = await policy.event(
            repair,
            "PAYMENT_RECEIVED",
            "receipt-event",
            payment_event={
                "id": "receipt-event",
                "payment_id": "receipt",
                "type": "PaymentReceived",
                "verified_amount": "100.00",
                "safe_reference": "REF-TEST",
            },
        )
        shipped = await policy.event(
            {**repair, "revision": 1}, "SHIPPED_TO_CUSTOMER", "shipping-event"
        )
        await db.repair_requests.update_one(
            {"id": "repair"},
            {
                "$set": {
                    "payment_receipt": repair["payment_receipt"],
                    "return_shipment": repair["return_shipment"],
                    "whatsapp_outbox": [receipt, shipped],
                }
            },
        )
        clock = [datetime.now(timezone.utc)]
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def transport(request):
            calls.append(json.loads(request.content)["template"]["name"])
            if len(calls) == 1:
                entered.set()
                await release.wait()
            return httpx.Response(
                200, json={"messages": [{"id": f"synthetic-{len(calls)}"}]}
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
            first = WhatsAppService(db, ACTIVE, http, clock=lambda: clock[0])
            second = WhatsAppService(db, ACTIVE, http, clock=lambda: clock[0])
            await first.reconcile()
            await db.whatsapp_jobs.update_one(
                {"_id": receipt["_id"]},
                {"$set": {"next_attempt_at": clock[0] - timedelta(seconds=1)}},
            )
            sending = asyncio.create_task(first.process_one())
            await asyncio.wait_for(entered.wait(), timeout=5)
            assert not await second.process_one()
            assert len(calls) == 1
            assert (await db.whatsapp_jobs.find_one({"_id": shipped["_id"]}))[
                "attempts"
            ] == 0
            release.set()
            await sending
            clock[0] += timedelta(seconds=3)
            assert await second.process_one()
        assert calls == [
            LIFECYCLE_CATALOG["PAYMENT_RECEIVED"]["name"],
            LIFECYCLE_CATALOG["SHIPPED_TO_CUSTOMER"]["name"],
        ]

    run(scenario, real=real)


def test_initial_activation_cannot_overwrite_a_concurrent_operator_scope():
    from services.lifecycle_control import change
    from services.lifecycle_readiness import INDEX_PLAN

    async def scenario(db):
        for collection, plans in INDEX_PLAN.items():
            for keys, options in plans:
                await db[collection].create_index(keys, **options)
        newer = replace(ACTIVE, activation_id="00000000-0000-4000-8000-000000000043")
        results = await asyncio.gather(
            change(db, ACTIVE, "activate", reviewed=True),
            change(db, newer, "activate", reviewed=True),
            return_exceptions=True,
        )
        assert (
            sum(
                isinstance(result, dict) and result.get("active") is True
                for result in results
            )
            == 1
        )
        assert await db.whatsapp_control.count_documents({}) == 1

    run(scenario, real=True)


@pytest.mark.parametrize(
    "uri",
    [
        "mongodb://127.0.0.1:27017,remote:27017",
        "mongodb://127.0.0.1:27017/?replicaSet=remote",
        "mongodb+srv://localhost/database",
        "mongodb://remote:27017",
    ],
)
def test_local_database_guard_rejects_discovery_and_nonlocal_seeds(uri):
    with pytest.raises((AssertionError, ValueError)):
        validate_local_uri(uri)


def test_readiness_accepts_existing_sparse_outbox_index():
    from services.lifecycle_readiness import missing_indexes

    async def scenario(db):
        worker = WhatsAppService(db, ACTIVE)
        await worker.initialize()
        await db.whatsapp_jobs.create_index(
            [
                ("activation_id", 1),
                ("repair_id", 1),
                ("source_revision", 1),
                ("state", 1),
            ]
        )
        assert not await missing_indexes(db)

    run(scenario)


def test_retired_activation_cannot_be_reused_after_an_intermediate_activation():
    from services.lifecycle_control import change
    from services.lifecycle_readiness import INDEX_PLAN

    async def scenario(db):
        policy, repair = await fixture(db)
        for collection, plans in INDEX_PLAN.items():
            for keys, options in plans:
                await db[collection].create_index(keys, **options)
        original = await policy.event(repair, "REQUESTED", "initial")
        newer = replace(ACTIVE, activation_id="00000000-0000-4000-8000-000000000043")
        await change(db, ACTIVE, "pause", reviewed=True)
        await change(db, newer, "activate", reviewed=True)
        await change(db, newer, "pause", reviewed=True)
        with pytest.raises(ValueError, match="Retired"):
            await change(db, ACTIVE, "activate", reviewed=True)
        assert await policy.reject_reason(original) == "activation_mismatch"

    run(scenario)


@pytest.mark.parametrize("failure_check", [1, 2])
def test_transient_control_lookup_defers_without_losing_or_ambiguating_job(
    failure_check,
):
    from unittest.mock import patch
    from pymongo.errors import AutoReconnect

    async def scenario(db):
        policy, repair = await fixture(db)
        job = await policy.event(repair, "REQUESTED", "initial")
        await db.repair_requests.update_one(
            {"id": "repair"}, {"$push": {"whatsapp_outbox": job}}
        )
        clock = [datetime.now(timezone.utc)]
        calls = []

        async def transport(request):
            calls.append(request)
            return httpx.Response(200, json={"messages": [{"id": "synthetic-review"}]})

        original = LifecyclePolicy.scope
        checks = 0

        async def unavailable(self, *args, **kwargs):
            nonlocal checks
            if kwargs.get("fail_on_error"):
                checks += 1
                if checks == failure_check:
                    raise AutoReconnect("synthetic")
            return await original(self, *args, **kwargs)

        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
            worker = WhatsAppService(db, ACTIVE, http, clock=lambda: clock[0])
            await worker.reconcile()
            with patch.object(LifecyclePolicy, "scope", unavailable):
                assert await worker.process_one()
            stored = await db.whatsapp_jobs.find_one({"_id": job["_id"]})
            assert stored["state"] == "pending" and stored["attempts"] == 0
            assert not stored.get("dispatch_started_at") and not calls
            clock[0] += timedelta(seconds=3)
            assert await worker.process_one()
        assert len(calls) == 1
        assert (await db.whatsapp_jobs.find_one({"_id": job["_id"]}))["state"] == "sent"

    run(scenario)


def test_test_template_with_no_parameters_omits_components_but_validates_snapshot():
    async def scenario(db):
        settings = replace(
            ACTIVE,
            mode="test",
            phone_number_id=ACTIVE.test_phone_number_id,
            test_recipients=(USER["phone"],),
            templates={
                **TEMPLATES,
                "REQUESTED": {
                    "name": "hello_world",
                    "language": "en_US",
                    "parameters": [],
                },
            },
        )
        policy, repair = await fixture(db, settings)
        job = await policy.event(repair, "REQUESTED", "initial")
        assert "components" not in message_payload(job, settings)["template"]
        job["values"]["customer_name"] = ""
        with pytest.raises(SnapshotError):
            message_payload(job, settings)

    run(scenario)


def test_shutdown_during_receipt_reconciliation_does_not_claim_another_job():
    from unittest.mock import AsyncMock, patch

    async def scenario(db):
        await fixture(db)
        stop = asyncio.Event()
        worker = WhatsAppService(db, ACTIVE)
        worker.reconcile = AsyncMock()

        async def receipts():
            stop.set()

        worker.apply_receipts = receipts
        worker.process_one = AsyncMock()
        with patch(
            "services.lifecycle_readiness.missing_indexes", AsyncMock(return_value=[])
        ):
            await worker.run(stop)
        worker.process_one.assert_not_awaited()

    run(scenario)


def test_creation_retry_list_and_detail_share_outage_state_without_losing_consent():
    from unittest.mock import patch
    from test_customer_profile import run as profile_run, sign_in
    import server

    async def scenario(auth, db, browser, clock):
        await sign_in(auth, db, browser, uid=USER["user_id"], phone=USER["phone"])
        policy = LifecyclePolicy(db, ACTIVE)
        await db.whatsapp_control.insert_one(
            {
                "_id": policy.scope_id(),
                "activation_id": ACTIVE.activation_id,
                "mode": ACTIVE.mode,
                "paused": False,
                "manifest_digest": digest(ACTIVE.templates),
                "instructions_digest": digest(instruction_preview(ACTIVE)),
                "heartbeat_at": datetime.now(timezone.utc),
            }
        )
        with patch.object(server.WhatsAppSettings, "from_env", return_value=ACTIVE):
            cap = (await browser.get("/api/customer/whatsapp-capability")).json()
            await db.whatsapp_control.update_one(
                {"_id": policy.scope_id()},
                {
                    "$set": {
                        "heartbeat_at": datetime.now(timezone.utc)
                        - timedelta(minutes=2)
                    }
                },
            )
            body = {
                "charger_info": {"brand": "Synthetic charger"},
                "problem_description": "Synthetic fault",
                "whatsapp_opt_in": True,
                "whatsapp_binding": cap["binding"],
                "idempotency_key": "outage-test",
            }
            created = await browser.post("/api/repairs", json=body)
            assert created.status_code == 200, created.text
            rid = created.json()["id"]
            retry = await browser.post("/api/repairs", json=body)
            detail = await browser.get(f"/api/repairs/{rid}")
            listing = (await browser.get("/api/repairs")).json()
            responses = [
                created.json(),
                retry.json(),
                detail.json(),
                next(r for r in listing if r["id"] == rid),
            ]
            assert all(
                r["whatsapp_updates"] == responses[0]["whatsapp_updates"]
                for r in responses
            )
            assert responses[0]["whatsapp_updates"]["state"] == "unavailable"
            assert all(
                "whatsapp_consent" not in r and "whatsapp_outbox" not in r
                for r in responses
            )
            stored = await db.repair_requests.find_one({"id": rid})
            assert (
                stored["whatsapp_consent"]["opted_in"] is True
                and len(stored["whatsapp_outbox"]) == 1
            )
            await db.whatsapp_control.update_one(
                {"_id": policy.scope_id()},
                {"$set": {"heartbeat_at": datetime.now(timezone.utc)}},
            )
            assert (await browser.get(f"/api/repairs/{rid}")).json()[
                "whatsapp_updates"
            ]["state"] == "enabled"
            assert (await browser.get("/api/repairs")).json()[0]["whatsapp_updates"][
                "state"
            ] == "enabled"

    profile_run(scenario)


@pytest.mark.parametrize(
    "charger_info", [{"brand": None, "model": None}, {"brand": "  ", "model": ""}]
)
@pytest.mark.parametrize("registered_name", ["Registered test charger", None])
def test_registered_charger_fills_blank_description_and_unregistered_whitespace_rejected(
    charger_info,
    registered_name,
):
    from test_customer_profile import run as profile_run, sign_in

    async def scenario(auth, db, browser, clock):
        await sign_in(auth, db, browser, uid=USER["user_id"], phone=USER["phone"])
        await db.chargers.insert_one(
            {"charger_id": "synthetic-charger", "name": registered_name}
        )
        response = await browser.post(
            "/api/repairs",
            json={
                "charger_id": "synthetic-charger",
                "charger_info": charger_info,
                "problem_description": "Synthetic fault",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["charger_info"]["brand"] == registered_name
        response = await browser.post(
            "/api/repairs",
            json={
                "charger_info": {"brand": "   "},
                "problem_description": "Synthetic fault",
            },
        )
        assert response.status_code == 400

    profile_run(scenario)


def test_notification_failures_do_not_abort_balance_or_receipt_and_log_no_details(
    caplog,
):
    from pymongo.errors import AutoReconnect

    async def scenario(db):
        await fixture(db, status="REPAIR_COMPLETED")

        async def broken(*args):
            raise AutoReconnect("sensitive synthetic text must not be logged")

        service = PaymentService(
            MongoPaymentRepository(db.repair_requests, db.payment_references),
            ManualPaymentProcessor(),
            notification_factory=broken,
            balance_notification_factory=broken,
        )
        assert await service.verify_balance(
            "repair", "100.00", "test reconciliation", "admin", "balance"
        ) == {"ok": True}
        await db.repair_requests.update_one(
            {"id": "repair"}, {"$set": {"status": "PAYMENT_PENDING"}}
        )
        result = await service.receive(
            "repair", "100.00", "cash", None, "admin", "receipt", True, VERIFIED
        )
        assert result["state"] == "PAID"
        stored = await db.repair_requests.find_one({"id": "repair"})
        assert (
            stored["payment_receipt"] and stored["payment_summary"]["state"] == "PAID"
        )
        assert not stored["whatsapp_outbox"]
        assert len(stored["whatsapp_notification_intents"]) == 2
        assert stored["completion_notice"]

    run(scenario)
    assert "balance_notification_construction_failed" in caplog.text
    assert "receipt_notification_construction_failed" in caplog.text
    assert "sensitive synthetic" not in caplog.text


def test_actual_control_read_error_is_transient_only_for_dispatch():
    from unittest.mock import AsyncMock
    from pymongo.errors import AutoReconnect

    async def scenario(db):
        policy, repair = await fixture(db)
        job = await policy.event(repair, "REQUESTED", "initial")
        policy.db = SimpleNamespace(
            whatsapp_control=SimpleNamespace(
                find_one=AsyncMock(side_effect=AutoReconnect("synthetic"))
            )
        )
        assert await policy.scope() is None
        assert await policy.reject_reason(job) == "activation_unavailable"

    run(scenario)


def test_requested_notification_matches_live_two_parameter_contract_for_registered_charger():
    async def scenario(db):
        policy, repair = await fixture(db)
        repair.update(
            charger_id="registered-id", charger_info={"brand": None, "model": "   "}
        )
        job = await policy.event(repair, "REQUESTED", "initial")
        assert set(job["values"]) == {"customer_name", "repair_number"}
        payload = message_payload(job, ACTIVE)
        assert payload["template"]["name"] == "rushx_repair_requested"
        assert payload["template"]["language"]["code"] == "en"
        assert len(payload["template"]["components"][0]["parameters"]) == 2

    run(scenario)


def test_sender_change_cannot_reuse_an_old_activation_to_revive_consent():
    async def scenario(db):
        policy, repair = await fixture(db)
        old_job = await policy.event(repair, "REQUESTED", "initial")
        moved = replace(ACTIVE, phone_number_id="999999", test_phone_number_id="999999")
        other = LifecyclePolicy(db, moved)
        assert other.scope_id() != policy.scope_id()
        scope = await db.whatsapp_control.find_one({"_id": policy.scope_id()})
        scope["_id"] = other.scope_id()
        await db.whatsapp_control.insert_one(scope)
        assert await other.scope()
        assert await other.event(repair, "REQUESTED", "after-move") is None
        assert await other.reject_reason(old_job) == "phone_changed"

    run(scenario)


@pytest.mark.parametrize("receipt", [False, True])
@pytest.mark.parametrize("real", [False, True])
def test_durable_payment_notification_intent_recovers_once_with_original_deadline(
    receipt, real
):
    from pymongo.errors import AutoReconnect

    async def scenario(db):
        policy, repair = await fixture(db, status="REPAIR_COMPLETED")

        async def broken(*args):
            raise AutoReconnect("synthetic")

        service = PaymentService(
            MongoPaymentRepository(db.repair_requests, db.payment_references),
            ManualPaymentProcessor(),
            notification_factory=broken,
            balance_notification_factory=None if receipt else broken,
        )
        await service.verify_balance(
            "repair", "100.00", "test reconciliation", "admin", "balance"
        )
        if receipt:
            await db.repair_requests.update_one(
                {"id": "repair"}, {"$set": {"status": "PAYMENT_PENDING"}}
            )
            await service.receive(
                "repair", "100.00", "cash", None, "admin", "receipt", True, VERIFIED
            )
            await service.receive(
                "repair", "100.00", "cash", None, "admin", "receipt", True, VERIFIED
            )
        else:
            await service.verify_balance(
                "repair", "100.00", "test reconciliation", "admin", "balance"
            )
        stored = await db.repair_requests.find_one({"id": "repair"})
        assert len(stored["whatsapp_notification_intents"]) == 1
        intent = stored["whatsapp_notification_intents"][0]
        calls = []

        async def transport(request):
            calls.append(request)
            return httpx.Response(200, json={"messages": [{"id": "synthetic-intent"}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
            worker = WhatsAppService(db, ACTIVE, http)
            await asyncio.gather(worker.reconcile(), worker.reconcile())
            assert await db.whatsapp_jobs.count_documents({}) == 1
            job = await db.whatsapp_jobs.find_one({})
            assert job["expires_at"] == intent["expires_at"]
            assert job["occurred_at"] == intent["occurred_at"]
            assert job["source_revision"] == intent["source_revision"]
            assert await worker.process_one()
            await worker.reconcile()
            assert not await worker.process_one()
        assert len(calls) == 1
        assert not (await db.repair_requests.find_one({"id": "repair"}))[
            "whatsapp_notification_intents"
        ]

    run(scenario, real=real)


@pytest.mark.parametrize("expired", [False, True])
def test_recovered_intent_still_respects_expiry_and_withdrawal(expired):
    async def scenario(db):
        await fixture(db, status="REPAIR_COMPLETED")

        async def broken(*args):
            raise RuntimeError("synthetic")

        service = PaymentService(
            MongoPaymentRepository(db.repair_requests, db.payment_references),
            ManualPaymentProcessor(),
            balance_notification_factory=broken,
        )
        await service.verify_balance(
            "repair", "100.00", "test reconciliation", "admin", "balance"
        )
        at = datetime.now(timezone.utc)
        if expired:
            at += timedelta(hours=25)
        else:
            await db.repair_requests.update_one(
                {"id": "repair"}, {"$set": {"whatsapp_consent.opted_in": False}}
            )
        worker = WhatsAppService(db, ACTIVE, clock=lambda: at)
        await worker.reconcile()
        if not expired:
            assert await worker.process_one()
        job = await db.whatsapp_jobs.find_one({})
        assert job["state"] == "suppressed"
        assert job["error_code"] == (
            "event_expired" if expired else "consent_withdrawn"
        )
        assert (await db.repair_requests.find_one({"id": "repair"}))[
            "completion_notice"
        ]

    run(scenario)


@pytest.mark.parametrize("real", [False, True])
def test_recovery_cursor_passes_two_hundred_deferred_repairs_and_wraps(real):
    from services.payment_service import notification_intent

    async def scenario(db):
        policy, repair = await fixture(db, status="REPAIR_COMPLETED")
        snapshot = {
            **repair,
            "payment_summary": {
                "amount_due": 100,
                "currency": "INR",
                "balance_state": "BALANCE_VERIFIED",
                "verified_at": "test",
                "verified_by": "admin",
            },
        }
        at = datetime.now(timezone.utc).isoformat()
        blocked = notification_intent(snapshot, "REPAIR_RESULT", "result", at)
        blocked["repair"]["whatsapp_consent"]["scope_id"] = "retired-sender"
        await db.repair_requests.insert_many(
            [
                {
                    "id": f"blocked-{i}",
                    "whatsapp_notification_intents": [deepcopy(blocked)],
                }
                for i in range(201)
            ]
        )
        eligible = notification_intent(
            {**snapshot, "id": "later-repair"}, "REPAIR_RESULT", "result", at
        )
        await db.repair_requests.insert_one(
            {"id": "later-repair", "whatsapp_notification_intents": [eligible]}
        )
        worker = WhatsAppService(db, ACTIVE)
        await worker.recover_notification_intents()
        assert not (await db.repair_requests.find_one({"id": "later-repair"})).get(
            "whatsapp_outbox"
        )
        await worker.recover_notification_intents()
        later = await db.repair_requests.find_one({"id": "later-repair"})
        assert (
            len(later["whatsapp_outbox"]) == 1
            and not later["whatsapp_notification_intents"]
        )
        assert (
            await db.repair_requests.count_documents(
                {"whatsapp_notification_intents._id": {"$exists": True}}
            )
            == 201
        )
        # A targeted ordering check does not disturb the rotating global cursor.
        cursor = worker._intent_cursor
        await worker.recover_notification_intents("blocked-0")
        assert worker._intent_cursor == cursor
        await worker.recover_notification_intents()
        assert worker._intent_cursor != cursor  # Wrapped to revisit deferred work.

    run(scenario, real=real)


def test_active_templates_require_the_exact_audited_locale_and_keep_legacy_locale():
    changed = deepcopy(TEMPLATES)
    changed["REQUESTED"]["language"] = "en_US"
    with pytest.raises(ConfigurationError):
        validate_settings(replace(ACTIVE, templates=changed))
    validate_settings(ACTIVE)
    validate_settings(SETTINGS)


def test_non_staging_modes_still_require_independent_meta_test_sender(monkeypatch):
    with pytest.raises(ConfigurationError):
        validate_settings(replace(ACTIVE, test_phone_number_id=""))
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ConfigurationError):
        validate_settings(
            replace(
                ACTIVE,
                mode="production",
                production_approved=True,
                test_phone_number_id="",
            )
        )


def test_staging_webhook_keeps_only_known_dispatched_stage_receipts_even_when_paused():
    import hashlib
    import hmac
    from fastapi import FastAPI
    from services.whatsapp_service import webhook_router

    async def scenario(db):
        settings = replace(ACTIVE, mode="staging", enabled=False, staging_enabled=False)
        await db.whatsapp_jobs.insert_many(
            [
                {
                    "_id": "stage-job",
                    "schema_version": 3,
                    "destination": USER["phone"],
                    "delivery_scope": {
                        "mode": "staging",
                        "phone_number_id": settings.phone_number_id,
                    },
                    "dispatch_started_at": datetime.now(timezone.utc),
                },
                {
                    "_id": "other-environment",
                    "schema_version": 3,
                    "destination": USER["phone"],
                    "delivery_scope": {
                        "mode": "production",
                        "phone_number_id": settings.phone_number_id,
                    },
                    "dispatch_started_at": datetime.now(timezone.utc),
                },
            ]
        )
        statuses = [
            {"id": "otp-message", "biz_opaque_callback_data": "unknown-job"},
            {
                "id": "production-message",
                "biz_opaque_callback_data": "other-environment",
            },
            {
                "id": "wrong-recipient",
                "biz_opaque_callback_data": "stage-job",
                "recipient_id": "919999999999",
            },
            {
                "id": "early-stage-message",
                "biz_opaque_callback_data": "stage-job",
                "recipient_id": USER["phone"].lstrip("+"),
            },
        ]
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {
                                    "phone_number_id": settings.phone_number_id
                                },
                                "statuses": [
                                    {
                                        **s,
                                        "status": "delivered",
                                        "timestamp": "1795100000",
                                    }
                                    for s in statuses
                                ],
                            }
                        }
                    ]
                }
            ],
        }
        raw = json.dumps(payload).encode()
        signature = (
            "sha256="
            + hmac.new(settings.app_secret.encode(), raw, hashlib.sha256).hexdigest()
        )
        app = FastAPI()
        app.include_router(webhook_router(lambda: db, lambda: settings), prefix="/api")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://test"
        ) as browser:
            response = await browser.post(
                "/api/webhooks/whatsapp",
                content=raw,
                headers={"X-Hub-Signature-256": signature},
            )
            assert response.status_code == 200, response.text
        receipts = await db.whatsapp_receipts.find({}).to_list(10)
        assert len(receipts) == 1 and receipts[0]["message_id"] == "early-stage-message"
        assert "recipient_id" not in receipts[0]

    run(scenario)


def test_active_catalog_matches_audited_live_templates_and_approved_submission_contracts():
    import re
    from pathlib import Path

    directory = (
        Path(__file__).resolve().parents[2] / "specs" / "whatsapp-lifecycle-updates"
    )
    audit = json.loads((directory / "live-template-audit.json").read_text())
    live = {t["name"]: t for t in audit["templates"]}
    proposed = {
        t["name"]: t
        for t in json.loads((directory / "meta-template-submission.json").read_text())[
            "templates"
        ]
    }
    reused = 0
    for item in LIFECYCLE_CATALOG.values():
        external = live.get(item["name"]) or proposed[item["name"]]
        if item["name"] in live:
            assert external["status"] == "APPROVED"
            reused += 1
        assert item["language"] == external["language"] == "en"
        assert external["category"] == "UTILITY"
        body = next(c["text"] for c in external["components"] if c["type"] == "BODY")
        assert item["body"] == body
        assert {int(i) for i in re.findall(r"\{\{(\d+)\}\}", body)} == set(
            range(1, len(item["parameters"]) + 1)
        )
        assert all(
            "{{" not in c.get("text", "")
            for c in external["components"]
            if c["type"] != "BODY"
        )
    assert reused == 5 and len(proposed) == 4
