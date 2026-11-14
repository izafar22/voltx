"""Staging preflight is pure and does not connect to Atlas."""
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
