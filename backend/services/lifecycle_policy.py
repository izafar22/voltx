"""Lifecycle v3 policy. Configuration and MongoDB checks never send provider HTTP."""

import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from pymongo.errors import PyMongoError

from .repair_facts import text_fact

SCHEMA_VERSION = 3
CONSENT_SOURCE = "repair_submission_v2"
PURPOSE = "repair_whatsapp_consent"


def verified_phone(user):
    return bool(
        user.get("phone_verified_at")
        and isinstance(user.get("phone"), str)
        and re.fullmatch(r"\+[1-9][0-9]{7,14}", user["phone"])
    )


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def instruction_preview(settings):
    address = settings.dispatch_address.strip()
    return (
        {"address": address, "digest": digest({"address": address, "version": 1})}
        if text_fact(address, 1024)
        else None
    )


def preference(repair, user):
    consent = repair.get("whatsapp_consent") or {}
    state = "not_enabled"
    if consent.get("opted_in"):
        state = "enabled"
        if consent.get("version") == 2 and not consent.get("activation_id"):
            state = "unavailable"
        elif (
            consent.get("version") != 2
            or not verified_phone(user)
            or consent.get("destination") != user.get("phone")
            or consent.get("phone_generation") != user.get("phone_generation", 0)
        ):
            state = "paused_phone_change"
    elif consent.get("withdrawn_at"):
        state = "stopped"
    phone = consent.get("destination", "")
    return {
        "state": state,
        "destination": ("••" + phone[-2:]) if phone else None,
        "can_stop": consent.get("opted_in") is True,
    }


class LifecyclePolicy:
    def __init__(self, db, settings, clock=None):
        self.db, self.settings = db, settings
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def scope_id(self):
        return "lifecycle:" + digest(
            [
                os.getenv("APP_ENV", "production"),
                self.settings.mode,
                self.settings.phone_number_id,
                os.getenv("DB_NAME", ""),
            ]
        )

    async def scope(self, heartbeat=False, fail_on_error=False):
        from .whatsapp_service import validate_settings, ConfigurationError

        s = self.settings
        if not s.enabled or not s.activation_id:
            return None
        try:
            validate_settings(s)
        except (ConfigurationError, ValueError, TypeError):
            return None
        try:
            scope = await self.db.whatsapp_control.find_one({"_id": self.scope_id()})
        except PyMongoError:
            if fail_on_error:
                raise
            return None
        if (
            not scope
            or scope.get("activation_id") != s.activation_id
            or scope.get("paused") is not False
            or scope.get("mode") != s.mode
            or scope.get("manifest_digest") != digest(s.templates)
            or scope.get("instructions_digest") != digest(instruction_preview(s))
        ):
            return None
        if s.mode == "staging":
            until = scope.get("test_until")
            if not isinstance(until, datetime):
                return None
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            if until <= self.clock():
                return None
        if heartbeat:
            at = scope.get("heartbeat_at")
            if not isinstance(at, datetime):
                return None
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            if at < self.clock() - timedelta(seconds=60):
                return None
        return scope

    async def capability(self, user, auth, request):
        available = bool(await self.scope(heartbeat=True))
        verified = verified_phone(user)
        result = {
            "available": available and verified,
            "reason_code": (
                "ready"
                if available and verified
                else ("verify_phone" if available and not verified else "unavailable")
            ),
            "destination": ("••" + user["phone"][-2:]) if verified else None,
            "identity_key": digest(
                [user.get("phone"), user.get("phone_generation", 0)]
            ),
            "binding": None,
        }
        if result["available"]:
            result["binding"] = jwt.encode(
                {
                    "purpose": PURPOSE,
                    "sub": user["user_id"],
                    "jti": secrets.token_urlsafe(16),
                    "session_id": auth.session_id(request),
                    "phone_generation": user.get("phone_generation", 0),
                    "destination_digest": digest(user["phone"]),
                    "consent_version": 2,
                    "exp": self.clock() + timedelta(minutes=10),
                },
                auth.settings.secret,
                algorithm="HS256",
            )
        return result

    async def consent(self, selected, binding, user, auth, request):
        if not selected:
            return {"opted_in": False, "version": 2, "revision": 0}
        try:
            data = auth.decode(binding or "", PURPOSE)
            valid = (
                data["sub"] == user["user_id"]
                and data.get("session_id") == auth.session_id(request)
                and data.get("phone_generation") == user.get("phone_generation", 0)
                and data.get("destination_digest") == digest(user.get("phone"))
                and data.get("consent_version") == 2
                and verified_phone(user)
            )
        except HTTPException:
            valid = False
        if not valid:
            raise HTTPException(
                409,
                {
                    "code": "whatsapp_eligibility_changed",
                    "message": "Review your verified mobile or submit without WhatsApp updates.",
                },
            )
        return {
            "opted_in": True,
            "version": 2,
            "revision": 0,
            "source": CONSENT_SOURCE,
            "at": self.clock().isoformat(),
            "destination": user["phone"],
            "phone_generation": user.get("phone_generation", 0),
            "activation_id": (
                self.settings.activation_id if await self.scope() else None
            ),
        }

    async def event(self, repair, status, event_id, customer=None, payment_event=None):
        from .whatsapp_service import event_for

        if not await self.scope():
            return None
        user = customer or await self.db.users.find_one({"user_id": repair["user_id"]})
        if not user or preference(repair, user)["state"] != "enabled":
            return None
        return event_for(repair, status, event_id, self.settings, user, payment_event)

    async def reject_reason(self, job):
        from .whatsapp_service import LOGICAL_LIFECYCLE_EVENTS

        s = self.settings
        if job.get("schema_version") != SCHEMA_VERSION:
            return "legacy_snapshot"
        if job.get("status") not in LOGICAL_LIFECYCLE_EVENTS:
            return "snapshot_invalid"
        try:
            scope = await self.scope(fail_on_error=True)
        except PyMongoError:
            return "activation_unavailable"
        if (
            job.get("activation_id") != s.activation_id
            or not scope
            or job.get("manifest_digest") != digest(s.templates)
        ):
            return "activation_mismatch"
        at = job.get("expires_at")
        if not isinstance(at, datetime):
            return "snapshot_invalid"
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        if at <= self.clock():
            return "event_expired"
        repair = await self.db.repair_requests.find_one({"id": job["repair_id"]})
        if not repair:
            return "repair_missing"
        if job.get("user_id") != repair.get("user_id"):
            return "recipient_ownership_changed"
        user = await self.db.users.find_one({"user_id": repair["user_id"]})
        if not user or user.get("status", "active") != "active":
            return "account_inactive"
        consent = repair.get("whatsapp_consent") or {}
        if consent.get("opted_in") is not True or consent.get("revision") != job.get(
            "consent_revision"
        ):
            return "consent_withdrawn"
        if (
            preference(repair, user)["state"] != "enabled"
            or consent.get("destination") != job.get("destination")
            or consent.get("activation_id") != job.get("activation_id")
            or user.get("phone_generation", 0) != job.get("phone_generation")
        ):
            return "phone_changed"
        if s.mode == "staging" and job.get("destination") not in s.staging_recipients:
            return "recipient_not_allowed"
        allowed = {
            "REQUESTED": {"REQUESTED"},
            "AWAITING_SHIPMENT": {"AWAITING_SHIPMENT"},
            "RECEIVED_AT_VOLTX": {"RECEIVED_AT_VOLTX", "DIAGNOSING"},
            "ESTIMATE_SENT": {"ESTIMATE_SENT"},
            "CUSTOMER_APPROVED": {"CUSTOMER_APPROVED", "REPAIRING"},
            "REPAIR_RESULT": {"REPAIR_COMPLETED", "PAYMENT_PENDING"},
            "SHIPPED_TO_CUSTOMER": {"SHIPPED_TO_CUSTOMER"},
        }
        if job["status"] in allowed and repair["status"] not in allowed[job["status"]]:
            return "event_superseded"
        if job["status"] == "AWAITING_SHIPMENT":
            if job.get("fact_digest") != digest(repair.get("intake_acceptance")):
                return "business_facts_changed"
        elif job["status"] in ("ESTIMATE_SENT", "CUSTOMER_APPROVED"):
            if job.get("fact_digest") != digest(
                {
                    k: v
                    for k, v in (repair.get("estimate") or {}).items()
                    if k not in ("status", "approved_at", "declined_at")
                }
            ):
                return "business_facts_changed"
        elif job["status"] == "REPAIR_RESULT":
            if job.get("fact_digest") != digest(repair.get("payment_summary")):
                return "business_facts_changed"
        elif job["status"] == "PAYMENT_RECEIVED":
            if job.get("receipt_id") != (repair.get("payment_receipt") or {}).get("id"):
                return "business_facts_changed"
        elif job["status"] == "SHIPPED_TO_CUSTOMER":
            if job.get("fact_digest") != digest(repair.get("return_shipment")):
                return "business_facts_changed"
        return None
