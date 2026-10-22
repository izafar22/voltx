from services.safety_indexes import initialize_safety_indexes
"""MongoDB semantics smoke test in a fresh disposable DB; Meta HTTP is mocked."""

import asyncio
import os
import secrets
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException
from services.payment_service import PaymentService, ManualPaymentProcessor
from services.payment_repository import MongoPaymentRepository
from services.whatsapp_service import payment_received_notification
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

from services.whatsapp_service import WhatsAppService
from test_whatsapp import SETTINGS, USER, ADMIN


def test_real_mongo_atomic_outbox_indexes_and_claims():
    async def scenario():
        import server

        url = (
            os.getenv("MONGO_URL")
            or dotenv_values(Path(__file__).parents[1] / ".env")["MONGO_URL"]
        )
        client = AsyncIOMotorClient(url, tz_aware=True, serverSelectionTimeoutMS=15000)
        name = "voltx_wa_test_" + secrets.token_hex(8)
        db = client[name]
        calls = []

        def send(request):
            calls.append(request)
            return httpx.Response(
                200, json={"messages": [{"id": f"wamid.{len(calls)}"}]}
            )

        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(send)) as http:
                svc = WhatsAppService(db, SETTINGS, http)
                await initialize_safety_indexes(db)
                await svc.initialize()
                await db.users.insert_one(dict(USER))
                with patch.object(server, "db", db), patch.object(
                    server.WhatsAppSettings, "from_env", return_value=SETTINGS
                ):
                    repair = await server.create_repair(
                        server.RepairCreate(
                            whatsapp_opt_in=True,
                            problem_description="Test charger fault",
                            charger_info={"brand": "Test"},
                        ),
                        USER,
                    )
                    for status in [
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
                    ]:
                        if status == "ESTIMATE_SENT":
                            await server.update_repair_estimate(
                                repair["id"], server.EstimateUpdate(labor=100), ADMIN
                            )
                        if status == "PAYMENT_PENDING":
                            await server.verify_repair_payment(
                                repair["id"],
                                server.PaymentVerification(
                                    amount_due=100, reference="test record"
                                ),
                                ADMIN,
                            )
                        if status == "SHIPPED_TO_CUSTOMER":
                            await server.update_repair_shipment(
                                repair["id"],
                                server.ShipmentUpdate(
                                    leg="return",
                                    courier="Example Courier",
                                    tracking_number="SAMPLE123",
                                ),
                                ADMIN,
                            )
                        await server.update_repair_status(
                            repair["id"],
                            server.RepairStatusUpdate(status=status),
                            ADMIN,
                        )
                await asyncio.gather(svc.reconcile(), svc.reconcile())
                assert await db.whatsapp_jobs.count_documents({}) == 8
                assert (await db.repair_requests.find_one({"id": repair["id"]}))[
                    "whatsapp_outbox"
                ] == []
                await asyncio.gather(*(svc.process_one() for _ in range(12)))
                assert len(calls) == 8
                assert await db.whatsapp_jobs.count_documents({"state": "sent"}) == 8
                assert not await svc.process_one()

                # Verify reference uniqueness and receipt/outbox CAS on real Mongo,
                # still using only the disposable DB and mocked Meta transport.
                original = await db.repair_requests.find_one({"id": repair["id"]})
                original.pop("_id")
                original["id"] = "duplicate-reference-test"
                await db.repair_requests.insert_one(original)
                payments = PaymentService(
                    MongoPaymentRepository(db.repair_requests, db.payment_references),
                    ManualPaymentProcessor(),
                    lambda r, event, customer: payment_received_notification(
                        r, event, SETTINGS, customer
                    ),
                )

                async def receipt(rid, key):
                    return await payments.receive(
                        rid,
                        100,
                        "upi",
                        "TESTUTR123456",
                        ADMIN["user_id"],
                        key,
                        True,
                        USER,
                    )

                results = await asyncio.gather(
                    *(receipt(repair["id"], "test-key") for _ in range(5))
                )
                assert len({result["payment_id"] for result in results}) == 1
                with pytest.raises(HTTPException) as conflict:
                    await receipt("duplicate-reference-test", "other-key")
                assert conflict.value.status_code == 409
                stored = await db.repair_requests.find_one({"id": repair["id"]})
                assert stored["payment_summary"]["state"] == "PAID"
                assert (
                    len(stored["payment_events"]) == len(stored["whatsapp_outbox"]) == 1
                )
                await asyncio.gather(svc.reconcile(), svc.reconcile())
                await asyncio.gather(*(svc.process_one() for _ in range(3)))
                assert len(calls) == 9
                assert await db.whatsapp_jobs.count_documents({"state": "sent"}) == 9
        finally:
            assert name.startswith("voltx_wa_test_")
            await client.drop_database(name)
            client.close()

    asyncio.run(scenario())
