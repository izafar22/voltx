"""Fail-closed staging configuration checks; no network or database I/O."""
import os
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
    if env.get("OTP_DELIVERY_PROVIDER", "none").lower() not in ("", "none"):
        raise RuntimeError("Staging OTP delivery must remain unconfigured")
    if env.get("WHATSAPP_ENABLED", "false").lower() != "false" or env.get("WHATSAPP_PRODUCTION_APPROVED", "false").lower() != "false":
        raise RuntimeError("Staging forbids outbound WhatsApp")
    if env.get("RUSHX_UPI_QR_REVIEWED", "false").lower() != "false":
        raise RuntimeError("Staging forbids approved merchant QR")
    if env.get("CMS_REVALIDATE_SECRET", ""):
        raise RuntimeError("Staging must not use a CMS revalidation secret")
    if env.get("CORS_ORIGINS") != "https://staging.evchargerrepair.in":
        raise RuntimeError("Staging requires the staging HTTPS origin")
