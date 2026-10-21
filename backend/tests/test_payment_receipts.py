"""Manual receipt, authorization, durable delivery and QR regressions."""

import asyncio
import json
from dataclasses import replace
from unittest.mock import patch
import httpx
import pytest
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient
from services.payment_service import PaymentService, ManualPaymentProcessor
from services.payment_repository import MongoPaymentRepository
from services.payment_config import public_payment_instructions
from services.whatsapp_service import (
    WhatsAppService,
    event_for,
    message_payload,
    payment_received_notification,
    ConfigurationError,
)
from test_whatsapp import run, SETTINGS, USER, ADMIN
from test_whatsapp_lifecycle import api_context, create


async def fixture(opt_in=True):
    db = AsyncMongoMockClient(tz_aware=True).test
    await db.repair_requests.insert_one(
        {
            "id": "r1",
            "user_id": USER["user_id"],
            "repair_request_number": "REP-10001",
            "status": "PAYMENT_PENDING",
            "revision": 0,
            "whatsapp_consent": {
                "opted_in": opt_in,
                "at": "test",
                "source": "repair_submission_v1",
                "destination": USER["phone"],
            },
        }
    )
    repo = MongoPaymentRepository(db.repair_requests, db.payment_references)
    service = PaymentService(
        repo,
        ManualPaymentProcessor(),
        lambda repair, event, customer: payment_received_notification(
            repair, event, SETTINGS, customer
        ),
    )
    await service.verify_balance("r1", 100, "balance review", "admin")
    return db, repo, service


async def receive(service, **overrides):
    args = dict(
        repair_id="r1",
        amount=100,
        method="upi",
        reference="UTR12345678",
        actor_id="admin",
        idempotency_key="one",
        funds_received=True,
        customer=USER,
    )
    return await service.receive(**{**args, **overrides})


def test_reference_unverified_then_one_receipt_event_and_mock_ack():
    async def check():
        db, repo, service = await fixture()
        await service.submit_reference("r1", "UTR12345678", USER["user_id"])
        repair = await repo.get("r1")
        assert repair["payment_summary"]["state"] == "AWAITING_MANUAL_VERIFICATION"
        assert not repair.get("payment_receipt") and not repair.get("whatsapp_outbox")
        results = await asyncio.gather(*(receive(service) for _ in range(5)))
        assert len({r["payment_id"] for r in results}) == 1
        repair = await repo.get("r1")
        assert repair["status"] == "PAYMENT_PENDING"
        assert repair["payment_summary"]["amount_due"] == 0
        assert repair["payment_receipt"]["state"] == "PAID"
        assert len(repair["payment_events"]) == len(repair["whatsapp_outbox"]) == 1
        calls = []

        async def handler(request):
            calls.append(request)
            return httpx.Response(200, json={"messages": [{"id": "mock-receipt"}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            worker = WhatsAppService(db, SETTINGS, http=http)
            await worker.initialize()
            await asyncio.gather(worker.reconcile(), worker.reconcile())
            assert await db.whatsapp_jobs.count_documents({}) == 1
            await worker.process_one()
            await worker.process_one()
        assert len(calls) == 1
        payload = json.loads(calls[0].content)
        assert payload["template"]["name"] == "rushx_payment_received_v1"
        assert [
            p["text"] for p in payload["template"]["components"][0]["parameters"]
        ] == ["Sample Customer", "REP-10001", "100.00", "REF-5678"]
        assert "UTR12345678" not in calls[0].content.decode()

    run(check)


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": 99},
        {"amount": 101},
        {"amount": 0},
        {"amount": True},
        {"amount": 100.001},
        {"reference": ""},
        {"reference": "bad\nUTR"},
        {"method": "card"},
        {"method": "cash", "reference": "external"},
        {"funds_received": False},
        {"idempotency_key": "\n"},
    ],
)
def test_invalid_receipt_no_writes(overrides):
    async def check():
        db, repo, service = await fixture()
        with pytest.raises(HTTPException):
            await receive(service, **overrides)
        assert not (await repo.get("r1")).get("payment_receipt")
        assert await db.payment_references.count_documents({}) == 0

    run(check)


def test_duplicate_reference_across_repairs_and_methods():
    async def check():
        db, repo, service = await fixture()
        second = await repo.get("r1")
        second.pop("_id")
        second["id"] = "r2"
        await db.repair_requests.insert_one(second)
        await receive(service)
        with pytest.raises(HTTPException) as error:
            await receive(
                service,
                repair_id="r2",
                method="bank_transfer",
                reference="utr12345678",
                idempotency_key="two",
            )
        assert error.value.status_code == 409
        assert not (await repo.get("r2")).get("payment_receipt")

    run(check)


def test_cash_id_and_no_consent():
    async def check():
        _, repo, service = await fixture(False)
        await receive(service, method="cash", reference=None)
        await receive(service, method="cash", reference=None)
        repair = await repo.get("r1")
        assert repair["payment_receipt"]["provider_reference"].startswith("CASH-")
        assert len(repair["payment_events"]) == 1 and not repair.get("whatsapp_outbox")

    run(check)


@pytest.mark.parametrize("stage", ["commit", "applied"])
def test_crash_retry_without_duplicate_settlement(stage):
    async def check():
        db, repo, service = await fixture()
        with patch.object(repo, stage, side_effect=RuntimeError("simulated crash")):
            with pytest.raises(RuntimeError):
                await receive(service)
        assert (await db.payment_references.find_one({}))["state"] == "RESERVED"
        await receive(service)
        repair = await repo.get("r1")
        assert len(repair["payment_events"]) == len(repair["whatsapp_outbox"]) == 1
        assert (await db.payment_references.find_one({}))["state"] == "APPLIED"

    run(check)


def test_cas_conflict_retry_rechecks_consent():
    async def check():
        _, repo, service = await fixture()
        commit = repo.commit

        async def race(repair, fields, pushes):
            await repo.repairs.update_one(
                {"id": "r1"},
                {"$set": {"whatsapp_consent.opted_in": False}, "$inc": {"revision": 1}},
            )
            return await commit(repair, fields, pushes)

        with patch.object(repo, "commit", side_effect=race):
            with pytest.raises(HTTPException) as error:
                await receive(service)
        assert error.value.status_code == 409
        assert not (await repo.get("r1")).get("payment_receipt")
        await receive(service)
        assert not (await repo.get("r1")).get("whatsapp_outbox")

    run(check)


def test_ack_separate_approval_gate():
    async def check():
        _, repo, service = await fixture()
        await receive(service)
        event = (await repo.get("r1"))["whatsapp_outbox"][0]
        settings = replace(
            SETTINGS,
            templates={
                k: v for k, v in SETTINGS.templates.items() if k != "PAYMENT_RECEIVED"
            },
        )
        with pytest.raises(ConfigurationError):
            message_payload(event, settings)

    run(check)


def test_qr_requires_separate_approved_media_template():
    async def check():
        _, repo, _ = await fixture()
        repair = await repo.get("r1")
        url = "https://merchant.example.test/rushx-qr.png"
        settings = replace(SETTINGS, payment_qr_url=url)
        assert "qr_image_url" not in event_for(
            repair, "PAYMENT_PENDING", "e", settings, USER
        )
        templates = {
            **settings.templates,
            "PAYMENT_PENDING_QR": {
                **settings.templates["PAYMENT_PENDING"],
                "name": "rushx_payment_pending_qr_v1",
                "header_format": "IMAGE",
            },
        }
        settings = replace(settings, templates=templates)
        event = event_for(repair, "PAYMENT_PENDING", "e", settings, USER)
        components = message_payload(event, settings)["template"]["components"]
        assert components[0] == {
            "type": "header",
            "parameters": [{"type": "image", "image": {"link": url}}],
        }
        assert components[1]["parameters"][-1]["text"] == "100.00"
        with pytest.raises(ConfigurationError):
            message_payload(event, replace(settings, payment_qr_url=""))

    run(check)


@pytest.mark.parametrize(
    "url,reviewed,expected",
    [
        ("", "true", False),
        ("https://merchant.example.test/qr.png", "false", False),
        ("https://merchant.example.test/qr.png", "true", True),
        ("http://merchant.example.test/qr.png", "true", False),
        ("https://user:secret@example.test/qr.png", "true", False),
        ("https://example.test/qr.png?token=secret", "true", False),
    ],
)
def test_qr_configuration(url, reviewed, expected):
    with patch.dict(
        "os.environ", {"RUSHX_UPI_QR_IMAGE_URL": url, "RUSHX_UPI_QR_REVIEWED": reviewed}
    ):
        assert bool(public_payment_instructions()["qr_image_url"]) == expected


def test_api_auth_customer_evidence_and_private_audit():
    async def check():
        async with api_context() as (db, browser, actor):
            rid = await create(browser)
            await db.repair_requests.update_one(
                {"id": rid},
                {"$set": {"status": "PAYMENT_PENDING", "whatsapp_outbox": []}},
            )
            actor[0] = ADMIN
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/payment",
                    json={"amount_due": 100, "reference": "review"},
                )
            ).status_code == 200
            payload = {
                "amount": 100,
                "method": "upi",
                "reference": "UTR12345678",
                "idempotency_key": "one",
                "funds_received": True,
            }
            actor[0] = USER
            assert (
                await browser.post(f"/api/repairs/{rid}/payment/verify", json=payload)
            ).status_code == 403
            assert (
                await browser.post(
                    f"/api/repairs/{rid}/payment/reference",
                    json={"reference": "UTR12345678"},
                )
            ).status_code == 200
            data = (await browser.get(f"/api/repairs/{rid}/payment")).json()
            assert (
                data["state"] == "AWAITING_MANUAL_VERIFICATION" and not data["receipt"]
            )
            actor[0] = {**USER, "user_id": "other"}
            assert (await browser.get(f"/api/repairs/{rid}/payment")).status_code == 403
            assert (
                await browser.post(
                    f"/api/repairs/{rid}/payment/reference",
                    json={"reference": "UTR000000"},
                )
            ).status_code == 403
            actor[0] = ADMIN
            assert (
                await browser.post(
                    f"/api/repairs/{rid}/payment/verify",
                    json={**payload, "amount": True},
                )
            ).status_code == 422
            for _ in range(2):
                response = await browser.post(
                    f"/api/repairs/{rid}/payment/verify", json=payload
                )
                assert response.status_code == 200, response.text
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/payment",
                    json={"amount_due": 50, "reference": "correction"},
                )
            ).status_code == 409
            actor[0] = USER
            data = (await browser.get(f"/api/repairs/{rid}/payment")).json()
            assert data["state"] == "PAID" and data["amount_due"] == 0
            assert (
                "audit" not in data
                and "verified_receipt" not in data
                and "UTR12345678" not in str(data)
            )

    run(check)


def test_reserved_key_cannot_be_reused_with_changed_reference():
    async def check():
        _, repo, service = await fixture()
        with patch.object(repo, "commit", side_effect=RuntimeError("crash")):
            with pytest.raises(RuntimeError):
                await receive(service)
        with pytest.raises(HTTPException) as error:
            await receive(service, reference="OTHER123456")
        assert error.value.status_code == 409
        assert not (await repo.get("r1")).get("payment_receipt")
        await receive(service)

    run(check)


@pytest.mark.parametrize("same_request", [True, False])
def test_overlapping_receipt_writers_cas(same_request):
    async def check():
        _, repo, service = await fixture()
        original_get = repo.get
        ready = asyncio.Event()
        reads = 0

        async def overlapping_read(repair_id):
            nonlocal reads
            repair = await original_get(repair_id)
            reads += 1
            if reads <= 2:
                if reads == 2:
                    ready.set()
                await ready.wait()
            return repair

        with patch.object(repo, "get", side_effect=overlapping_read):
            second = (
                {}
                if same_request
                else {"reference": "OTHER123456", "idempotency_key": "two"}
            )
            results = await asyncio.gather(
                receive(service), receive(service, **second), return_exceptions=True
            )
        repair = await original_get("r1")
        assert len(repair["payment_events"]) == len(repair["whatsapp_outbox"]) == 1
        if same_request:
            assert results[0] == results[1]
        else:
            assert (
                sum(
                    isinstance(item, HTTPException) and item.status_code == 409
                    for item in results
                )
                == 1
            )

    run(check)


def test_pre_pending_receipt_is_rejected_and_paid_balance_cancels_stale_request():
    async def check():
        db, repo, service = await fixture()
        repair = await repo.get("r1")
        request = event_for(repair, "PAYMENT_PENDING", "pending", SETTINGS, USER)
        await repo.repairs.update_one(
            {"id": "r1"}, {"$set": {"status": "REPAIR_COMPLETED"}}
        )
        with pytest.raises(HTTPException):
            await receive(service)
        await repo.repairs.update_one(
            {"id": "r1"},
            {"$set": {"status": "PAYMENT_PENDING", "whatsapp_outbox": [request]}},
        )
        await receive(service)

        def unexpected(request):
            raise AssertionError("No stale payment request may reach Meta")

        async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected)) as http:
            worker = WhatsAppService(db, SETTINGS, http=http)
            await worker.reconcile()
            # Restrict this check to the pending request; acknowledgement is tested separately.
            await db.whatsapp_jobs.delete_many({"status": "PAYMENT_RECEIVED"})
            await worker.process_one()
        job = await db.whatsapp_jobs.find_one({"status": "PAYMENT_PENDING"})
        assert job["error_code"] == "business_facts_changed"

    run(check)


def test_withdrawal_after_settlement_blocks_ack():
    async def check():
        db, repo, service = await fixture()
        await receive(service)
        await repo.repairs.update_one(
            {"id": "r1"}, {"$set": {"whatsapp_consent.opted_in": False}}
        )

        def unexpected(request):
            raise AssertionError("Consent withdrawn")

        async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected)) as http:
            worker = WhatsAppService(db, SETTINGS, http=http)
            await worker.reconcile()
            await worker.process_one()
        assert (await db.whatsapp_jobs.find_one({}))["error_code"] == "consent_invalid"

    run(check)


def test_provider_neutral_receipt_uses_same_event_and_outbox():
    class TestVerifiedProcessor:
        async def verify_receipt(self, amount, method, reference):
            return {
                "provider": "test_verified_adapter",
                "amount": amount,
                "method": method,
                "reference": reference,
            }

    async def check():
        _, repo, service = await fixture()
        service.processor = TestVerifiedProcessor()
        await receive(service)
        repair = await repo.get("r1")
        assert repair["payment_receipt"]["provider"] == "test_verified_adapter"
        assert repair["payment_events"][0]["type"] == "PaymentReceived"
        assert repair["whatsapp_outbox"][0]["status"] == "PAYMENT_RECEIVED"

    run(check)


def test_disabled_whatsapp_still_records_authoritative_domain_event():
    async def check():
        _, repo, service = await fixture()
        service.notification_factory = (
            lambda repair, event, customer: payment_received_notification(
                repair, event, replace(SETTINGS, enabled=False), customer
            )
        )
        await receive(service)
        repair = await repo.get("r1")
        assert len(repair["payment_events"]) == 1
        assert not repair.get("whatsapp_outbox")

    run(check)


def test_malformed_qr_environment_does_not_break_payment_or_repair_configuration():
    with patch.dict(
        "os.environ",
        {"RUSHX_UPI_QR_IMAGE_URL": "https://[invalid", "RUSHX_UPI_QR_REVIEWED": "true"},
    ):
        assert public_payment_instructions()["qr_image_url"] is None
