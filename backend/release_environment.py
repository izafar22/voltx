"""Offline runtime preflight for the operator-provisioned Oracle service."""
import os
import re
from urllib.parse import parse_qs, unquote, urlsplit

if __package__:
    from .auth_service import AuthSettings
    from .staging_safety import validate_staging_environment
else:
    from auth_service import AuthSettings
    from staging_safety import validate_staging_environment


def validate_release_environment(expected, env):
    if expected not in ("production", "staging") or env.get("APP_ENV") != expected:
        raise RuntimeError("Service APP_ENV does not match this Oracle host")
    if expected == "staging":
        validate_staging_environment(env)
        if env.get("OTP_DELIVERY_PROVIDER", "none").lower() == "whatsapp":
            if (env.get("WHATSAPP_PHONE_NUMBER_ID") != env.get("RUSHX_EXPECTED_STAGING_WHATSAPP_SENDER") or
                    not re.fullmatch(r"[a-z0-9_]+", env.get("WHATSAPP_OTP_TEMPLATE", "")) or
                    not re.fullmatch(r"[a-z]{2}(?:_[A-Z]{2})?", env.get("WHATSAPP_OTP_LANGUAGE", "")) or
                    not re.fullmatch(r"v[0-9]+\.[0-9]+", env.get("WHATSAPP_API_VERSION", "v25.0"))):
                raise RuntimeError("Staging OTP requires the approved test sender and explicit template settings")
    else:
        # These expectations must be set from an independent, operator-reviewed
        # production inventory, never derived by parsing the live URI.
        host = env.get("RUSHX_EXPECTED_ATLAS_HOST", "").lower()
        user = env.get("RUSHX_EXPECTED_ATLAS_USER", "")
        database = env.get("RUSHX_EXPECTED_DATABASE", "")
        try:
            uri = urlsplit(env.get("MONGO_URL", ""))
            valid = (uri.scheme == "mongodb+srv" and uri.hostname == host and
                     uri.port is None and unquote(uri.username or "") == user and
                     bool(uri.password) and unquote(uri.path) in ("", "/", "/" + database))
        except ValueError:
            valid = False
        if (not valid or not host.endswith(".mongodb.net") or not user or not database or
                "staging" in (host + user + database).lower() or env.get("DB_NAME") != database):
            raise RuntimeError("Production requires the approved production Atlas destination")
    origins = tuple(part.strip().rstrip("/") for part in env.get("CORS_ORIGINS", "").split(","))
    AuthSettings(env.get("JWT_SECRET", ""), expected, env.get("OTP_MODE", "provider"),
                 env.get("EXPOSE_DEMO_OTP", "false").lower() != "false", origins).validate()
    if expected == "staging":
        google = [env.get(key, "") for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI")]
        if any(google) and (not all(google) or google[2] != origins[0] + "/api/auth/google/callback"):
            raise RuntimeError("Google Sign-In requires the staging HTTPS callback and complete credentials")
    uri = urlsplit(env["MONGO_URL"])
    options = {key.lower(): values for key, values in parse_qs(uri.query, keep_blank_values=True).items()}
    if (uri.scheme != "mongodb+srv" or uri.port is not None or
            unquote(uri.path) not in ("", "/", "/" + env["DB_NAME"]) or
            any(key in options for key in ("tlsinsecure", "tlsallowinvalidcertificates",
                                          "tlsallowinvalidhostnames", "srvservicename")) or
            any(value.lower() != "true" for key in ("tls", "ssl") for value in options.get(key, []))):
        raise RuntimeError("Oracle releases require Atlas SRV and verified TLS")


if __name__ == "__main__":
    try:
        validate_release_environment(os.environ.get("RUSHX_RELEASE_ENVIRONMENT"), os.environ)
    except (RuntimeError, ValueError):
        # Even malformed configuration must not disclose URI or credentials.
        raise SystemExit("Oracle service configuration rejected. Check the deployment runbook.") from None
