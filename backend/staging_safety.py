"""Fail-closed staging configuration checks; no network or database I/O."""
import os
import re
from urllib.parse import unquote, urlsplit


def validate_staging_environment(env=None):
    env = os.environ if env is None else env
    if env.get("APP_ENV") != "staging":
        return
    uri = env.get("MONGO_URL", "")
    try:
        parsed = urlsplit(uri)
        valid_uri = (
            parsed.scheme in ("mongodb+srv", "mongodb")
            and unquote(parsed.username or "") == "rushx_staging_app"
            and (parsed.hostname or "").lower() == "voltx-staging.ovofwvn.mongodb.net"
            and bool(parsed.password)
        )
    except ValueError:
        valid_uri = False
    if env.get("DB_NAME") != "rushx_staging" or not valid_uri:
        raise RuntimeError("Staging requires the dedicated Atlas user, host and database")
    if env.get("OTP_MODE", "provider") != "provider" or env.get("EXPOSE_DEMO_OTP", "false").lower() != "false":
        raise RuntimeError("Staging forbids demo OTP")
    provider = env.get("OTP_DELIVERY_PROVIDER", "none").lower()
    if provider not in ("", "none", "whatsapp"):
        raise RuntimeError("Unsupported staging OTP delivery provider")
    if provider == "whatsapp":
        phones = [p.strip() for p in env.get("STAGING_OTP_ALLOWED_PHONES", "").split(",")]
        if (not phones or any(not re.fullmatch(r"\+91[6-9][0-9]{9}", p) for p in phones)
                or len(phones) != len(set(phones)) or len(phones) > 10):
            raise RuntimeError("Staging WhatsApp OTP requires 1-10 unique allowlisted Indian numbers")
        if not env.get("WHATSAPP_ACCESS_TOKEN", "").strip() or not re.fullmatch(
                r"[0-9]+", env.get("WHATSAPP_PHONE_NUMBER_ID", "")):
            raise RuntimeError("Staging WhatsApp OTP credentials are missing or invalid")
    elif env.get("STAGING_OTP_ALLOWED_PHONES", "").strip():
        raise RuntimeError("Staging OTP allowlist requires WhatsApp provider")
    if env.get("WHATSAPP_ENABLED", "false").lower() != "false" or env.get("WHATSAPP_PRODUCTION_APPROVED", "false").lower() != "false":
        raise RuntimeError("Staging forbids outbound WhatsApp")
    if env.get("RUSHX_UPI_QR_REVIEWED", "false").lower() != "false":
        raise RuntimeError("Staging forbids approved merchant QR")
    if env.get("CMS_REVALIDATE_SECRET", ""):
        raise RuntimeError("Staging must not use a CMS revalidation secret")
    if env.get("CORS_ORIGINS") != "https://staging.evchargerrepair.in":
        raise RuntimeError("Staging requires the staging HTTPS origin")
