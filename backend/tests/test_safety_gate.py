"""PR #4 pre-merge regressions; isolated Mongo mocks, no money or provider I/O."""

import asyncio
from dataclasses import replace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
import server
from test_whatsapp import run, USER, ADMIN
from test_whatsapp_lifecycle import api_context, create


@pytest.mark.parametrize(
    "endpoint,body",
    [
        ("/wallet/topup", {"amount": 100}),
        ("/sessions/start", {"charger_id": "x"}),
        ("/sessions/x/stop", {}),
        ("/owner/withdraw", {"amount": 1}),
        ("/admin/wallet/adjust", {"user_id": "customer", "amount": 1}),
        ("/admin/withdrawals/x", {"status": "paid"}),
    ],
)
def test_production_simulated_finance_is_denied_without_writes(endpoint, body):
    async def check():
        async with api_context() as (db, browser, actor):
            actor[0] = ADMIN
            with patch.object(
                server,
                "auth_settings",
                replace(server.auth_settings, environment="production"),
            ):
                response = await (
                    browser.patch(endpoint.replace("/admin", "/api/admin"), json=body)
                    if endpoint.startswith("/admin/withdrawals")
                    else browser.post("/api" + endpoint, json=body)
                )
            assert response.status_code == 403, response.text
            for name in (
                "wallets",
                "transactions",
                "owner_wallets",
                "withdrawals",
                "sessions",
            ):
                assert await db[name].count_documents({}) == 0

    run(check)


def test_creation_idempotency_concurrency_and_conflict():
    async def check():
        async with api_context() as (db, browser, actor):
            body = {
                "charger_info": {"brand": "Test"},
                "problem_description": "test fault",
                "idempotency_key": "same",
                "whatsapp_opt_in": True,
            }
            responses = await asyncio.gather(
                *(browser.post("/api/repairs", json=body) for _ in range(8))
            )
            assert all(r.status_code == 200 for r in responses)
            assert len({r.json()["id"] for r in responses}) == 1
            repair = await db.repair_requests.find_one({})
            assert len(repair["status_history"]) == len(repair["whatsapp_outbox"]) == 1
            assert "creation_key" not in responses[0].json()
            assert (
                await browser.post(
                    "/api/repairs", json={**body, "problem_description": "different"}
                )
            ).status_code == 409
            actor[0] = {**USER, "user_id": "another"}
            assert (await browser.post("/api/repairs", json=body)).json()[
                "id"
            ] != repair["id"]

    run(check)


@pytest.mark.parametrize("role", ["customer", "owner", "unsupported"])
def test_cross_user_read_and_mutation_denied(role):
    async def check():
        async with api_context() as (db, browser, actor):
            rid = await create(browser)
            actor[0] = {**USER, "user_id": "intruder", "role": role}
            assert (await browser.get(f"/api/repairs/{rid}")).status_code == 403
            for path, body in [
                ("status", {"status": "AWAITING_SHIPMENT"}),
                ("diagnosis", {"diagnosis": "x"}),
                ("estimate", {"labor": 1}),
                ("shipment", {"leg": "incoming", "courier": "x"}),
                ("shipment", {"leg": "return", "courier": "x"}),
                ("payment", {"amount_due": 1, "reference": "test"}),
            ]:
                assert (
                    await browser.patch(f"/api/repairs/{rid}/{path}", json=body)
                ).status_code == 403
            assert (
                await browser.delete(f"/api/repairs/{rid}/whatsapp-consent")
            ).status_code == 403
            assert (await browser.get("/api/repairs?scope=all")).status_code == 403

    run(check)


def test_owner_relationship_read_is_minimal_and_cannot_mutate_customer_repair():
    async def check():
        async with api_context() as (db, browser, actor):
            rid = await create(browser)
            await db.chargers.insert_one({"charger_id": "owned", "owner_id": "owner"})
            await db.repair_requests.update_one(
                {"id": rid},
                {
                    "$set": {
                        "charger_id": "owned",
                        "incoming_shipment": {"notes": "private"},
                        "problem_description": "private",
                    }
                },
            )
            actor[0] = {"user_id": "owner", "role": "owner"}
            data = (await browser.get(f"/api/repairs/{rid}")).json()
            assert (
                data["id"] == rid
                and "private" not in str(data)
                and "user_id" not in data
            )
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/status", json={"status": "CANCELLED"}
                )
            ).status_code == 403
            actor[0] = USER
            # Reporting a public registered charger is an existing supported flow;
            # it grants no ownership or access to another customer's repair.
            response = await browser.post(
                "/api/repairs",
                json={"charger_id": "owned", "problem_description": "test"},
            )
            assert response.status_code == 200
            assert response.json()["user_id"] == USER["user_id"]
            assert not await server.can_access_repair({}, {"user_id": None})
            assert not await server.can_access_repair(USER, {"user_id": None})

    run(check)


def test_state_guards_private_fields_and_quote_minor_units():
    async def check():
        async with api_context() as (db, browser, actor):
            rid = await create(browser)
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/shipment",
                    json={"leg": "incoming", "received_date": "today"},
                )
            ).status_code == 403
            await db.repair_requests.update_one(
                {"id": rid}, {"$set": {"status": "RECEIVED_AT_VOLTX"}}
            )
            assert (
                await browser.patch(
                    f"/api/repairs/{rid}/shipment",
                    json={"leg": "incoming", "courier": "x"},
                )
            ).status_code == 409
            actor[0] = ADMIN
            response = await browser.patch(
                f"/api/repairs/{rid}/estimate",
                json={
                    "parts": [{"name": "part", "qty": 3, "price": 0.1}],
                    "labor": 0.2,
                    "notes": "private",
                },
            )
            assert response.json()["estimate"]["total_minor"] == 50
            await browser.patch(
                f"/api/repairs/{rid}/diagnosis",
                json={"internal_notes": "private", "technician_notes": "private"},
            )
            await db.repair_requests.update_one(
                {"id": rid}, {"$set": {"status": "COMPLETED"}}
            )
            for path, body in [
                ("estimate", {"labor": 1}),
                ("diagnosis", {"diagnosis": "changed"}),
                ("shipment", {"leg": "return", "courier": "changed"}),
            ]:
                assert (
                    await browser.patch(f"/api/repairs/{rid}/{path}", json=body)
                ).status_code == 409
            actor[0] = USER
            assert "private" not in str(
                (await browser.get(f"/api/repairs/{rid}")).json()
            )

    run(check)


def test_diagnosis_cas_rejects_concurrent_closure():
    async def check():
        async with api_context() as (db, browser, actor):
            rid = await create(browser)
            collection = db.repair_requests
            original = collection.update_one

            async def raced(query, update):
                await original(
                    {"id": rid},
                    {"$set": {"status": "CANCELLED"}, "$inc": {"revision": 1}},
                )
                return await original(query, update)

            from types import SimpleNamespace

            with patch.object(
                server, "db", SimpleNamespace(repair_requests=collection)
            ), patch.object(collection, "update_one", side_effect=raced):
                with pytest.raises(HTTPException) as error:
                    await server.update_repair_diagnosis(
                        rid, server.DiagnosisUpdate(diagnosis="test"), ADMIN
                    )
            assert error.value.status_code == 409
            assert not (await collection.find_one({"id": rid}))["diagnosis"]

    run(check)


def test_cursor_pagination_ties_projection_scope_and_index_startup():
    async def check():
        async with api_context() as (db, browser, actor):
            for i in range(5):
                await db.repair_requests.insert_one(
                    {
                        "id": str(i),
                        "user_id": USER["user_id"],
                        "status": "REQUESTED",
                        "created_at": "same",
                        "photos": ["large"],
                        "payment_records": [{"private": "secret"}],
                    }
                )
            seen = []
            cursor = None
            while True:
                response = await browser.get(
                    "/api/repairs",
                    params={"limit": 2, **({"cursor": cursor} if cursor else {})},
                )
                assert response.status_code == 200, response.text
                for row in response.json():
                    assert "photos" not in row and "payment_records" not in row
                    seen.append(row["id"])
                cursor = response.headers.get("x-next-cursor")
                if not cursor:
                    break
            assert seen == ["4", "3", "2", "1", "0"]
            assert (await browser.get("/api/repairs?scope=bogus")).status_code == 400
            assert (await browser.get("/api/repairs?cursor=invalid")).status_code == 400
            assert (await browser.get("/api/repairs?limit=101")).status_code == 422
            indexes = await db.payment_references.index_information()
            assert indexes["repair_payment_idempotency"]["unique"]

    run(check)


@pytest.mark.parametrize("value", [0.001, "100.0000000000000001", True])
def test_fractional_paise_or_boolean_cannot_enter_new_quotes(value):
    from pydantic import ValidationError

    with pytest.raises((HTTPException, ValidationError)):
        server.EstimateUpdate(labor=value)
    with pytest.raises((HTTPException, ValidationError)):
        server.PaymentVerification(amount_due=value, reference="review")


def test_unsupported_role_cannot_access_own_payment_or_consent():
    async def check():
        async with api_context() as (_, browser, actor):
            rid = await create(browser)
            actor[0] = {**USER, "role": "unsupported"}
            assert (await browser.get(f"/api/repairs/{rid}/payment")).status_code == 403
            assert (
                await browser.post(
                    f"/api/repairs/{rid}/payment/reference",
                    json={"reference": "TEST123"},
                )
            ).status_code == 403
            assert (
                await browser.delete(f"/api/repairs/{rid}/whatsapp-consent")
            ).status_code == 403

    run(check)


def test_paid_cancellation_requires_review():
    async def check():
        async with api_context() as (db, browser, actor):
            rid = await create(browser)
            await db.repair_requests.update_one(
                {"id": rid},
                {
                    "$set": {
                        "status": "PAYMENT_PENDING",
                        "payment_receipt": {"state": "PAID"},
                    }
                },
            )
            for user in (USER, ADMIN):
                actor[0] = user
                assert (
                    await browser.patch(
                        f"/api/repairs/{rid}/status", json={"status": "CANCELLED"}
                    )
                ).status_code == 409
            assert (await db.repair_requests.find_one({"id": rid}))[
                "status"
            ] == "PAYMENT_PENDING"

    run(check)


def test_payment_requests_do_not_create_indexes():
    from test_payment_receipts import fixture, receive

    async def check():
        _, repo, service = await fixture()
        with patch.object(
            repo.references,
            "create_index",
            side_effect=AssertionError("DDL in request"),
        ):
            assert (await receive(service))["state"] == "PAID"

    run(check)


def test_duplicate_legacy_index_data_fails_without_destructive_repair():
    from mongomock_motor import AsyncMongoMockClient
    from pymongo.errors import DuplicateKeyError
    from services.safety_indexes import initialize_safety_indexes

    async def check():
        db = AsyncMongoMockClient().test
        for i in range(2):
            await db.payment_references.insert_one(
                {
                    "_id": str(i),
                    "repair_id": "same",
                    "receipt": {"idempotency_key": "same"},
                }
            )
        with pytest.raises(DuplicateKeyError):
            await initialize_safety_indexes(db)
        assert await db.payment_references.count_documents({}) == 2

    run(check)


@pytest.mark.parametrize("host", ["example.test/api/webhooks/whatsapp#", "example.test/api/webhooks/whatsapp?"])
def test_host_cannot_bypass_origin_guard(host):
    async def check():
        async with api_context() as (db, browser, actor):
            response = await browser.post(
                "/api/wallet/topup", json={"amount": 100},
                headers={"host": host, "origin": "https://untrusted.invalid"},
            )
            assert response.status_code == 403
            assert response.json()["detail"] == "Request origin is not allowed"
            assert await db.transactions.count_documents({}) == 0
    run(check)


def test_host_cannot_hide_auth_cache_protection():
    async def check():
        async with api_context() as (db, browser, actor):
            response = await browser.get(
                "/api/auth/me", headers={"host": "example.test/unrelated#"}
            )
            assert response.headers["cache-control"] == "no-store"
    run(check)
