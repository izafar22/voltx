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
    if env.get("WHATSAPP_PRODUCTION_APPROVED", "false").lower() != "false":
        raise RuntimeError("Staging forbids production messaging approval")
    if env.get("WHATSAPP_ENABLED", "false").lower() != "false":
        recipients = [x.strip() for x in env.get('STAGING_LIFECYCLE_ALLOWED_PHONES', '').split(',')]
        if (env.get('WHATSAPP_LIFECYCLE_ENABLED', 'false').lower() != 'true'
                or env.get('STAGING_LIFECYCLE_TEST_ENABLED', 'false').lower() != 'true'
                or env.get('WHATSAPP_MODE') != 'staging'
                or not env.get('WHATSAPP_LIFECYCLE_ACTIVATION_ID', '').strip()
                or not re.fullmatch(r'[0-9]+', env.get('STAGING_LIFECYCLE_PHONE_NUMBER_ID', ''))
                or env.get('WHATSAPP_PHONE_NUMBER_ID') != env.get('STAGING_LIFECYCLE_PHONE_NUMBER_ID')
                or not 1 <= len(recipients) <= 10 or len(recipients) != len(set(recipients))
                or any(not re.fullmatch(r'\+91[6-9][0-9]{9}', p) for p in recipients)):
            raise RuntimeError('Staging lifecycle messages require the isolated authorized test gate')
    elif env.get("STAGING_LIFECYCLE_CONTINUOUS_ENABLED", "false").lower() != "false":
        raise RuntimeError("Continuous staging lifecycle requires WhatsApp delivery gates")
    if env.get("RUSHX_UPI_QR_REVIEWED", "false").lower() == "true":
        qr = urlsplit(env.get("RUSHX_UPI_QR_IMAGE_URL", ""))
        if (
            env.get("WHATSAPP_PAYMENT_QR_ENABLED", "false").lower() != "true"
            or env.get("WHATSAPP_ENABLED", "false").lower() != "true"
            or qr.scheme != "https"
            or qr.netloc.lower() != "staging.evchargerrepair.in"
            or not qr.path.startswith("/payment-assets/")
            or any(unquote(segment) in (".", "..") for segment in qr.path.split("/"))
            or qr.query
            or qr.fragment
        ):
            raise RuntimeError("Staging merchant QR requires the reviewed isolated asset gate")
    if env.get("CMS_REVALIDATE_SECRET", ""):
        raise RuntimeError("Staging must not use a CMS revalidation secret")
    if env.get("CORS_ORIGINS") != "https://staging.evchargerrepair.in":
        raise RuntimeError("Staging requires the staging HTTPS origin")
