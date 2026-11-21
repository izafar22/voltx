"""The staging payment exception stays bounded to an active lifecycle test."""

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, patch

from mongomock_motor import AsyncMongoMockClient

import server
from services.lifecycle_policy import LifecyclePolicy
from test_whatsapp import PHONE, SETTINGS

STAGING_SETTINGS = replace(
    SETTINGS,
    mode="staging",
    staging_enabled=True,
    staging_sender=SETTINGS.phone_number_id,
    staging_recipients=(PHONE,),
    activation_id="11111111-1111-4111-8111-111111111111",
)


def run(coro):
    return asyncio.run(coro)


def test_active_bound_repair_payment_is_allowed(monkeypatch):
    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).test
        monkeypatch.setenv("APP_ENV", "staging")
        monkeypatch.setenv("DB_NAME", "rushx_staging")
        policy = LifecyclePolicy(db, STAGING_SETTINGS)
        await db.repair_requests.insert_one(
            {
                "id": "rep_test",
                "user_id": "customer",
                "whatsapp_consent": {
                    "opted_in": True,
                    "version": 2,
                    "activation_id": STAGING_SETTINGS.activation_id,
                    "scope_id": policy.scope_id(),
                    "destination": PHONE,
                    "phone_generation": 0,
                },
            }
        )
        await db.users.insert_one(
            {
                "user_id": "customer",
                "phone": PHONE,
                "phone_generation": 0,
                "phone_verified_at": "2026-11-21T00:00:00+00:00",
            }
        )
        scope = AsyncMock(return_value={"active": True})
        with (
            patch.object(server, "db", db),
            patch.object(
                server.WhatsAppSettings, "from_env", return_value=STAGING_SETTINGS
            ),
            patch.object(server.LifecyclePolicy, "scope", scope),
        ):
            for suffix in ("", "/", "/reference", "/verify"):
                assert await server.staging_lifecycle_payment_allowed(
                    f"/api/repairs/rep_test/payment{suffix}"
                )
        assert scope.await_count == 4
        assert all(call.kwargs == {"heartbeat": True} for call in scope.await_args_list)

    run(scenario())


def test_payment_gate_fails_closed(monkeypatch):
    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).test
        monkeypatch.setenv("APP_ENV", "staging")
        monkeypatch.setenv("DB_NAME", "rushx_staging")
        policy = LifecyclePolicy(db, STAGING_SETTINGS)
        await db.repair_requests.insert_one(
            {
                "id": "rep_test",
                "user_id": "customer",
                "whatsapp_consent": {
                    "opted_in": True,
                    "version": 2,
                    "activation_id": STAGING_SETTINGS.activation_id,
                    "scope_id": policy.scope_id(),
                    "destination": PHONE,
                    "phone_generation": 0,
                },
            }
        )
        await db.users.insert_one(
            {
                "user_id": "customer",
                "phone": PHONE,
                "phone_generation": 0,
                "phone_verified_at": "2026-11-21T00:00:00+00:00",
            }
        )
        with (
            patch.object(server, "db", db),
            patch.object(
                server.WhatsAppSettings, "from_env", return_value=STAGING_SETTINGS
            ),
            patch.object(server.LifecyclePolicy, "scope", AsyncMock(return_value=None)),
        ):
            assert not await server.staging_lifecycle_payment_allowed(
                "/api/repairs/rep_test/payment"
            )
        await db.repair_requests.update_one(
            {"id": "rep_test"},
            {"$set": {"whatsapp_consent.destination": "+919999999999"}},
        )
        with (
            patch.object(server, "db", db),
            patch.object(
                server.WhatsAppSettings, "from_env", return_value=STAGING_SETTINGS
            ),
            patch.object(server.LifecyclePolicy, "scope", AsyncMock(return_value={})),
        ):
            assert not await server.staging_lifecycle_payment_allowed(
                "/api/repairs/rep_test/payment/verify"
            )
            assert not await server.staging_lifecycle_payment_allowed(
                "/api/wallet/topup"
            )
            assert not await server.staging_lifecycle_payment_allowed(
                "/api/repairs/other/payment"
            )

    run(scenario())


def test_production_or_disabled_settings_never_open_gate():
    async def scenario():
        for settings in (
            replace(STAGING_SETTINGS, mode="production", production_approved=True),
            replace(STAGING_SETTINGS, enabled=False),
            replace(STAGING_SETTINGS, staging_enabled=False),
        ):
            with patch.object(
                server.WhatsAppSettings, "from_env", return_value=settings
            ):
                assert not await server.staging_lifecycle_payment_allowed(
                    "/api/repairs/rep_test/payment"
                )

    run(scenario())
