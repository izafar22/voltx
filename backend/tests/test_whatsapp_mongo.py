"""MongoDB semantics smoke test in a fresh disposable DB; Meta HTTP is mocked."""

import asyncio
import os
import secrets
from pathlib import Path
from unittest.mock import patch

import httpx
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
                await svc.initialize()
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
                    ]:
                        await server.update_repair_status(
                            repair["id"],
                            server.RepairStatusUpdate(status=status),
                            ADMIN,
                        )
                await asyncio.gather(svc.reconcile(), svc.reconcile())
                assert await db.whatsapp_jobs.count_documents({}) == 2
                assert (await db.repair_requests.find_one({"id": repair["id"]}))[
                    "whatsapp_outbox"
                ] == []
                await asyncio.gather(
                    svc.process_one(), svc.process_one(), svc.process_one()
                )
                assert len(calls) == 2
                assert await db.whatsapp_jobs.count_documents({"state": "sent"}) == 2
                assert not await svc.process_one()
        finally:
            assert name.startswith("voltx_wa_test_")
            await client.drop_database(name)
            client.close()

    asyncio.run(scenario())
