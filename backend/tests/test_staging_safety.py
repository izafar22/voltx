"""Staging preflight is pure and does not connect to Atlas."""
import asyncio

import pytest

from auth_service import AuthSettings
from staging_safety import validate_staging_environment


@pytest.fixture
def safe_env():
    return {
        "APP_ENV": "staging",
        "MONGO_URL": "mongodb+srv://rushx_staging_app:dummy@voltx-staging.ovofwvn.mongodb.net/?authSource=admin",
        "DB_NAME": "rushx_staging",
        "OTP_MODE": "provider",
        "OTP_DELIVERY_PROVIDER": "none",
        "EXPOSE_DEMO_OTP": "false",
        "WHATSAPP_ENABLED": "false",
        "WHATSAPP_PRODUCTION_APPROVED": "false",
        "RUSHX_UPI_QR_REVIEWED": "false",
        "CORS_ORIGINS": "https://staging.evchargerrepair.in",
    }


def test_valid_staging_configuration(safe_env):
    validate_staging_environment(safe_env)
    AuthSettings("x" * 32, "staging", "provider", False,
                 ("https://staging.evchargerrepair.in",)).validate()


@pytest.mark.parametrize("key,value", [
    ("DB_NAME", "rushx_production"),
    ("MONGO_URL", "mongodb+srv://prod:pass@voltx-staging.ovofwvn.mongodb.net"),
    ("MONGO_URL", "mongodb+srv://rushx_staging_app:pass@production.example.com"),
    ("OTP_MODE", "demo"),
    ("EXPOSE_DEMO_OTP", "true"),
    ("OTP_DELIVERY_PROVIDER", "smtp"),
    ("WHATSAPP_ENABLED", "true"),
    ("WHATSAPP_PRODUCTION_APPROVED", "true"),
    ("RUSHX_UPI_QR_REVIEWED", "true"),
    ("CMS_REVALIDATE_SECRET", "production-secret"),
    ("CORS_ORIGINS", "https://evchargerrepair.in"),
])
def test_unsafe_staging_configuration_rejected(safe_env, key, value):
    safe_env[key] = value
    with pytest.raises(RuntimeError):
        validate_staging_environment(safe_env)


def test_production_configuration_not_changed(safe_env):
    safe_env["APP_ENV"] = "production"
    safe_env["DB_NAME"] = "rushx_production"
    validate_staging_environment(safe_env)


@pytest.mark.parametrize("otp_mode,expose,origins", [
    ("demo", False, ("https://staging.evchargerrepair.in",)),
    ("provider", True, ("https://staging.evchargerrepair.in",)),
    ("provider", False, ("http://localhost:3000",)),
])
def test_staging_auth_hardening(otp_mode, expose, origins):
    with pytest.raises(RuntimeError):
        AuthSettings("x" * 32, "staging", otp_mode, expose, origins).validate()


def test_staging_whatsapp_otp_requires_allowlist_and_credentials(safe_env):
    safe_env["OTP_DELIVERY_PROVIDER"] = "whatsapp"
    with pytest.raises(RuntimeError):
        validate_staging_environment(safe_env)
    safe_env["STAGING_OTP_ALLOWED_PHONES"] = "+919876543210"
    with pytest.raises(RuntimeError):
        validate_staging_environment(safe_env)
    safe_env["WHATSAPP_ACCESS_TOKEN"] = "test-only-token"
    safe_env["WHATSAPP_PHONE_NUMBER_ID"] = "123456789"
    validate_staging_environment(safe_env)


@pytest.mark.parametrize("phones", [
    "", "+919876543210,+919876543210", "+919876543210,+12025550123",
    "9876543210", "+919876543210,not-a-number",
])
def test_staging_whatsapp_otp_rejects_bad_allowlist(safe_env, phones):
    safe_env.update({
        "OTP_DELIVERY_PROVIDER": "whatsapp",
        "STAGING_OTP_ALLOWED_PHONES": phones,
        "WHATSAPP_ACCESS_TOKEN": "test-only-token",
        "WHATSAPP_PHONE_NUMBER_ID": "123456789",
    })
    with pytest.raises(RuntimeError):
        validate_staging_environment(safe_env)


def test_staging_allowlist_cannot_be_enabled_without_provider(safe_env):
    safe_env["STAGING_OTP_ALLOWED_PHONES"] = "+919876543210"
    with pytest.raises(RuntimeError):
        validate_staging_environment(safe_env)


def test_staging_whatsapp_otp_still_blocks_repair_notifications(safe_env):
    safe_env.update({
        "OTP_DELIVERY_PROVIDER": "whatsapp",
        "STAGING_OTP_ALLOWED_PHONES": "+919876543210",
        "WHATSAPP_ACCESS_TOKEN": "test-only-token",
        "WHATSAPP_PHONE_NUMBER_ID": "123456789",
        "WHATSAPP_ENABLED": "true",
    })
    with pytest.raises(RuntimeError):
        validate_staging_environment(safe_env)


def test_release_preflight_blocks_other_senders_and_invalid_templates(safe_env):
    from release_environment import validate_release_environment

    safe_env.update({
        "JWT_SECRET": "x" * 32,
        "OTP_DELIVERY_PROVIDER": "whatsapp",
        "STAGING_OTP_ALLOWED_PHONES": "+919000000001",
        "WHATSAPP_ACCESS_TOKEN": "test-only-token",
        "WHATSAPP_PHONE_NUMBER_ID": "123456789",
        "RUSHX_EXPECTED_STAGING_WHATSAPP_SENDER": "123456789",
        "WHATSAPP_OTP_TEMPLATE": "staging_otp",
        "WHATSAPP_OTP_LANGUAGE": "en_US",
    })
    validate_release_environment("staging", safe_env)
    for key, value in (("WHATSAPP_PHONE_NUMBER_ID", "987654321"), ("WHATSAPP_OTP_TEMPLATE", ""),
                       ("WHATSAPP_OTP_LANGUAGE", "invalid"), ("GOOGLE_CLIENT_ID", "partial"),
                       ("MONGO_URL", safe_env["MONGO_URL"] + "&tls=false"), ("APP_ENV", "production")):
        with pytest.raises(RuntimeError):
            validate_release_environment("staging", {**safe_env, key: value})


def test_staging_whatsapp_mocked_send_and_non_allowlisted_denial(safe_env, monkeypatch):
    import httpx
    from fastapi import HTTPException
    from mongomock_motor import AsyncMongoMockClient
    from auth_service import AuthService

    monkeypatch.setenv("OTP_DELIVERY_PROVIDER", "whatsapp")
    monkeypatch.setenv("STAGING_OTP_ALLOWED_PHONES", "+919000000001")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-only-token")
    monkeypatch.setenv("WHATSAPP_OTP_TEMPLATE", "staging_otp")
    monkeypatch.setenv("WHATSAPP_OTP_LANGUAGE", "en_US")
    payloads = []

    async def fake_post(self, url, json, headers):
        assert url.startswith("https://graph.facebook.com/") and url.endswith("/123/messages")
        assert headers["Authorization"] == "Bearer test-only-token"
        payloads.append(json)
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    db = AsyncMongoMockClient(tz_aware=True).db
    service = AuthService(db, AuthSettings("x" * 32, "staging", origins=(safe_env["CORS_ORIGINS"],)))
    async def scenario():
        with pytest.raises(HTTPException) as denied:
            await service.request_otp("+919000000002", "test")
        assert denied.value.status_code == 403
        assert await db.auth_limits.count_documents({}) == 0
        assert payloads == []
        await service.request_otp("+919000000001", "test")

    asyncio.run(scenario())
    [payload] = payloads
    assert payload["to"] == "919000000001"
    template = payload["template"]
    assert template["name"] == "staging_otp" and template["language"] == {"code": "en_US"}
    assert [component["type"] for component in template["components"]] == ["body", "button"]


def test_production_preflight_checks_approved_atlas_inventory():
    from release_environment import validate_release_environment

    env = {
        "APP_ENV": "production",
        "JWT_SECRET": "x" * 32,
        "CORS_ORIGINS": "https://evchargerrepair.in",
        "MONGO_URL": "mongodb+srv://dummy_user:dummy@approved.example.mongodb.net",
        "DB_NAME": "example_live",
        "RUSHX_EXPECTED_ATLAS_HOST": "approved.example.mongodb.net",
        "RUSHX_EXPECTED_ATLAS_USER": "dummy_user",
        "RUSHX_EXPECTED_DATABASE": "example_live",
    }
    validate_release_environment("production", env)
    for key, value in (("DB_NAME", "rushx_staging"), ("RUSHX_EXPECTED_ATLAS_USER", "other"),
                       ("MONGO_URL", env["MONGO_URL"].replace("approved", "wrong")),
                       ("MONGO_URL", env["MONGO_URL"] + "/?tlsInsecure=true")):
        with pytest.raises(RuntimeError):
            validate_release_environment("production", {**env, key: value})
