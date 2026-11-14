"""Payment boundary regressions; all persistence and provider calls are mocked."""

import asyncio
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient
from services.payment_service import (
    ManualPaymentProcessor,
    PaymentService,
    VerifiedBalance,
)
from services.payment_repository import MongoPaymentRepository
from services.repair_facts import amount_due
from test_whatsapp import run, ADMIN
from test_whatsapp_lifecycle import api_context, create


async def fixture():
    collection = AsyncMongoMockClient().test.repairs
    await collection.insert_one(
        {"id": "r1", "status": "REPAIR_COMPLETED", "revision": 0}
    )
    return collection, PaymentService(
        MongoPaymentRepository(collection, AsyncMongoMockClient().test.references),
        ManualPaymentProcessor(),
    )


def test_records_corrections_and_zero_balance():
    async def check():
        collection, service = await fixture()
        for amount in (100, 40, 0, 20):
            await service.verify_balance("r1", amount, f"review {amount}", "admin")
        repair = await collection.find_one({"id": "r1"})
        assert repair["status"] == "REPAIR_COMPLETED"
        assert repair["revision"] == 4
        assert amount_due(repair) == "20.00"
        records = repair["payment_records"]
        assert len(records) == 4
        for record in records:
            assert record["verified_amount"] == record["amount_due"]
            assert record["verified_amount_kind"] == "outstanding_balance"
            assert record["state"] == "BALANCE_VERIFIED"
            assert record["currency"] == "INR"
            assert record["audit"]["verified_by"] == "admin"
        assert records[-1]["audit"]["supersedes"] == records[-2]["id"]

    run(check)


def test_concurrent_duplicates_and_conflicting_key():
    async def check():
        collection, service = await fixture()
        await asyncio.gather(
            *(
                service.verify_balance("r1", 100, "review", "admin", "key")
                for _ in range(10)
            )
        )
        await collection.update_one({"id": "r1"}, {"$set": {"status": "COMPLETED"}})
        assert await service.verify_balance("r1", 100, "review", "admin", "key") == {
            "ok": True
        }
        repair = await collection.find_one({"id": "r1"})
        assert len(repair["payment_records"]) == 1 and repair["revision"] == 1
        with pytest.raises(HTTPException) as error:
            await service.verify_balance("r1", 99, "review", "admin", "key")
        assert error.value.status_code == 409

    run(check)


@pytest.mark.parametrize(
    "amount,reference,key",
    [
        (-1, "valid", None),
        (float("nan"), "valid", None),
        (True, "valid", None),
        (100000000, "valid", None),
        (1, "   ", None),
        (1, "a\nb", None),
        (1, "valid", "\n"),
    ],
)
def test_validation(amount, reference, key):
    async def check():
        collection, service = await fixture()
        with pytest.raises(HTTPException):
            await service.verify_balance("r1", amount, reference, "admin", key)
        assert (await collection.find_one({"id": "r1"}))["revision"] == 0

    run(check)


def test_competing_write():
    async def check():
        collection, service = await fixture()
        original = collection.update_one

        async def race(query, update):
            await original(
                {"id": "r1"}, {"$inc": {"revision": 1}, "$set": {"status": "CANCELLED"}}
            )
            return await original(query, update)

        with patch.object(collection, "update_one", side_effect=race):
            with pytest.raises(HTTPException) as error:
                await service.verify_balance("r1", 100, "review", "admin")
        assert error.value.status_code == 409
        repair = await collection.find_one({"id": "r1"})
        assert "payment_summary" not in repair and "payment_records" not in repair

    run(check)


def test_legacy_and_provider_neutral_balance():
    legacy = {
        "source": "manual_reconciliation",
        "currency": "INR",
        "amount_due": 25,
        "verified_at": "timestamp",
        "verified_by": "admin",
    }
    assert amount_due({"payment_summary": legacy}) == "25.00"
    assert (
        amount_due(
            {
                "payment_summary": {
                    **legacy,
                    "source": "test",
                    "balance_state": "BALANCE_VERIFIED",
                }
            }
        )
        == "25.00"
    )
    for overrides in (
        {"balance_state": "PENDING"},
        {"amount_due": 0},
        {"currency": "USD"},
    ):
        with pytest.raises(HTTPException):
            amount_due({"payment_summary": {**legacy, **overrides}})


def test_injected_processor():
    class TestProcessor:
        async def verify_balance(self, amount_due, reference):
            return VerifiedBalance(
                amount_due, "test_adapter", "test", "BALANCE_VERIFIED"
            )

    async def check():
        collection, _ = await fixture()
        await PaymentService(
            MongoPaymentRepository(collection, AsyncMongoMockClient().test.references),
            TestProcessor(),
        ).verify_balance("r1", 12, "review", "admin")
        assert amount_due(await collection.find_one({"id": "r1"})) == "12.00"

    run(check)


def test_api_auth_privacy_legacy_retry_and_consent():
    async def check():
        async with api_context() as (db, browser, actor):
            rid = await create(browser, opt_in=False)
            await db.repair_requests.update_one(
                {"id": rid}, {"$set": {"status": "REPAIR_COMPLETED"}}
            )
            payload = {"amount_due": 100, "reference": "manual review"}
            assert (
                await browser.patch(f"/api/repairs/{rid}/payment", json=payload)
            ).status_code == 403
            actor[0] = ADMIN
            for _ in range(2):
                response = await browser.patch(
                    f"/api/repairs/{rid}/payment", json=payload
                )
                assert response.status_code == 200, response.text
                assert response.json() == {"ok": True}
            repair = await db.repair_requests.find_one({"id": rid})
            assert len(repair["payment_records"]) == 1
            assert not repair.get("whatsapp_outbox")
            response = await browser.get(f"/api/repairs/{rid}")
            assert "payment_records" not in response.json()
            assert set(response.json()["payment_summary"]) == {
                "amount_due",
                "currency",
                "verified_at",
            }

    run(check)
