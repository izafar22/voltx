"""RushX notification outbox. No network I/O occurs in repair request handlers."""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)
E164 = re.compile(r"\+[1-9][0-9]{7,14}\Z")
# Only explicitly supported customer events. No diagnosis, notes, cost or courier claims.
STATUS_TEXT = {
    "REQUESTED": "RushX has received your repair request",
    "RECEIVED_AT_VOLTX": "Your charger has been received at RushX",
    "DIAGNOSING": "RushX is diagnosing your charger",
    "ESTIMATE_SENT": "Your RushX repair estimate is ready to review in the app",
    "REPAIR_COMPLETED": "RushX has completed your charger repair",
    "SHIPPED_TO_CUSTOMER": "RushX has marked your charger as shipped",
}
RANK = {"sent": 1, "failed": 2, "delivered": 3, "read": 4}


class WebhookAccessLogFilter(logging.Filter):
    """Uvicorn access logging must not record Meta's verification-token query."""

    def filter(self, record):
        args = record.args
        if isinstance(args, tuple) and len(args) == 5 and isinstance(args[2], str):
            path = args[2]
            if path.split("?", 1)[0] == "/api/webhooks/whatsapp":
                record.args = (*args[:2], path.split("?", 1)[0], *args[3:])
        return True


def now():
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Settings:
    enabled: bool = False
    access_token: str = field(default="", repr=False)
    phone_number_id: str = ""
    verify_token: str = field(default="", repr=False)
    app_secret: str = field(default="", repr=False)
    api_version: str = ""
    dispatch_address: str = ""
    templates: dict = field(default_factory=dict)
    mode: str = "test"
    test_recipients: tuple = ()
    max_attempts: int = 5

    @classmethod
    def from_env(cls):
        # Invalid configuration must not break existing repair routes.
        try:
            templates = json.loads(os.getenv("WHATSAPP_TEMPLATES_JSON", "{}"))
        except (TypeError, ValueError):
            templates = {}
        return cls(
            enabled=os.getenv("WHATSAPP_ENABLED", "false").lower() == "true",
            access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
            phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
            verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN", ""),
            app_secret=os.getenv("META_APP_SECRET", ""),
            api_version=os.getenv("WHATSAPP_API_VERSION", ""),
            dispatch_address=os.getenv("RUSHX_DISPATCH_ADDRESS", ""),
            templates=templates if isinstance(templates, dict) else {},
            mode=os.getenv("WHATSAPP_MODE", "test"),
            test_recipients=tuple(
                x.strip()
                for x in os.getenv("WHATSAPP_TEST_RECIPIENTS", "").split(",")
                if x.strip()
            ),
        )


def consent_record(opt_in, user, at):
    if not opt_in:
        return {"opted_in": False}
    phone = user.get("phone", "")
    if not isinstance(phone, str) or not E164.fullmatch(phone):
        raise HTTPException(
            422,
            "WhatsApp updates require a valid international phone number on your account",
        )
    return {
        "opted_in": True,
        "at": at,
        "source": "repair_submission_v1",
        "destination": phone,
    }


def event_for(repair, status, event_id, settings):
    consent = repair.get("whatsapp_consent", {})
    if not settings.enabled or not consent.get("opted_in") or status not in STATUS_TEXT:
        return None
    return {
        "_id": (
            f"{repair['id']}:REQUESTED"
            if status == "REQUESTED"
            else f"{repair['id']}:{event_id}"
        ),
        "repair_id": repair["id"],
        "event_id": event_id,
        "status": status,
        "destination": consent["destination"],
        "consent_at": consent["at"],
        "values": {
            "repair_number": repair["repair_request_number"],
            "dispatch_address": settings.dispatch_address,
            "status_text": STATUS_TEXT[status],
        },
    }


class ConfigurationError(Exception):
    pass


def message_payload(job, settings):
    if (
        not settings.access_token
        or not re.fullmatch(r"[0-9]+", settings.phone_number_id)
        or not re.fullmatch(r"v[0-9]+\.[0-9]+", settings.api_version)
        or not settings.app_secret
        or not settings.verify_token
    ):
        raise ConfigurationError()
    if settings.mode not in ("test", "production"):
        raise ConfigurationError()
    if settings.mode == "test" and job["destination"] not in settings.test_recipients:
        raise ConfigurationError()
    template = settings.templates.get(job["status"], {})
    if (
        not isinstance(template, dict)
        or not re.fullmatch(r"[a-z0-9_]+", template.get("name", ""))
        or not re.fullmatch(r"[a-z]{2,3}(?:_[A-Z]{2})?", template.get("language", ""))
    ):
        raise ConfigurationError()
    params = template.get("parameters")
    if not isinstance(params, list) or any(p not in job["values"] for p in params):
        raise ConfigurationError()
    # hello_world is a deliberate sandbox-only smoke test with no parameters.
    sandbox = (
        settings.mode == "test" and template["name"] == "hello_world" and params == []
    )
    required = (
        {"repair_number", "dispatch_address"}
        if job["status"] == "REQUESTED"
        else {"repair_number"}
    )
    if not sandbox and (
        not required.issubset(params) or any(not job["values"][p] for p in params)
    ):
        raise ConfigurationError()
    body = {"name": template["name"], "language": {"code": template["language"]}}
    if params:
        body["components"] = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": job["values"][p]} for p in params
                ],
            }
        ]
    return {
        "messaging_product": "whatsapp",
        "to": job["destination"],
        "type": "template",
        "template": body,
        "biz_opaque_callback_data": job["_id"],
    }


class WhatsAppService:
    def __init__(self, db, settings, http=None, clock=now):
        self.db, self.settings, self.http, self.clock = db, settings, http, clock

    async def initialize(self):
        await self.db.whatsapp_jobs.create_index([("state", 1), ("next_attempt_at", 1)])
        await self.db.whatsapp_jobs.create_index("message_id", sparse=True)
        await self.db.repair_requests.create_index("whatsapp_outbox._id", sparse=True)
        await self.db.whatsapp_receipts.create_index(
            [("processed", 1), ("next_check_at", 1)]
        )

    async def reconcile(self):
        # Embedded events and the business mutation are a single Mongo document write.
        # Remove ONLY after idempotent upsert; crashes on either side are recoverable.
        async for repair in self.db.repair_requests.find(
            {"whatsapp_outbox._id": {"$exists": True}}, {"id": 1, "whatsapp_outbox": 1}
        ).limit(200):
            for event in repair["whatsapp_outbox"]:
                try:
                    await self.db.whatsapp_jobs.update_one(
                        {"_id": event["_id"]},
                        {
                            "$setOnInsert": {
                                **event,
                                "state": "pending",
                                "attempts": 0,
                                "created_at": self.clock(),
                                "next_attempt_at": self.clock(),
                                "delivery_rank": 0,
                            }
                        },
                        upsert=True,
                    )
                except DuplicateKeyError:
                    pass  # another reconciler already materialized this event
                await self.db.repair_requests.update_one(
                    {"id": repair["id"]},
                    {"$pull": {"whatsapp_outbox": {"_id": event["_id"]}}},
                )

    async def apply_receipts(self):
        async for receipt in (
            self.db.whatsapp_receipts.find(
                {"processed": False, "next_check_at": {"$lte": self.clock()}}
            )
            .sort("next_check_at", 1)
            .limit(200)
        ):
            query = {"message_id": receipt["message_id"]}
            if receipt.get("job_id"):
                query = {"$or": [query, {"_id": receipt["job_id"]}]}
            job = await self.db.whatsapp_jobs.find_one(query)
            if not job:
                await self.db.whatsapp_receipts.update_one(
                    {"_id": receipt["_id"]},
                    {"$set": {"next_check_at": self.clock() + timedelta(seconds=60)}},
                )
                continue  # callback may arrive before send acknowledgement/reconciliation
            if receipt["rank"] > job.get("delivery_rank", 0):
                await self.db.whatsapp_jobs.update_one(
                    {"_id": job["_id"], "delivery_rank": {"$lt": receipt["rank"]}},
                    {
                        "$set": {
                            "delivery_rank": receipt["rank"],
                            "state": receipt["status"],
                            "message_id": receipt["message_id"],
                            "delivery_at": receipt["timestamp"],
                        }
                    },
                )
            await self.db.whatsapp_receipts.update_one(
                {"_id": receipt["_id"]}, {"$set": {"processed": True}}
            )

    async def process_one(self):
        if not self.settings.enabled:
            return False
        at, lease = self.clock(), uuid.uuid4().hex
        job = await self.db.whatsapp_jobs.find_one_and_update(
            {
                "$or": [
                    {
                        "state": {"$in": ["pending", "retryable_failure"]},
                        "next_attempt_at": {"$lte": at},
                    },
                    {"state": "processing", "lease_until": {"$lte": at}},
                ]
            },
            {
                "$set": {
                    "state": "processing",
                    "lease": lease,
                    "lease_until": at + timedelta(seconds=120),
                },
                "$inc": {"attempts": 1},
            },
            return_document=ReturnDocument.AFTER,
        )
        if not job:
            return False
        claim = {"_id": job["_id"], "lease": lease, "state": "processing"}

        async def finish(values):
            await self.db.whatsapp_jobs.update_one(
                claim,
                {
                    "$set": {**values, "updated_at": self.clock()},
                    "$unset": {"lease": "", "lease_until": ""},
                },
            )

        if job["attempts"] > self.settings.max_attempts:
            await finish({"state": "dead_letter", "error_code": "attempts_exhausted"})
            return True
        repair = await self.db.repair_requests.find_one(
            {"id": job["repair_id"]}, {"whatsapp_consent": 1}
        )
        consent = (repair or {}).get("whatsapp_consent", {})
        if (
            consent.get("opted_in") is not True
            or consent.get("at") != job.get("consent_at")
            or consent.get("source") != "repair_submission_v1"
            or consent.get("destination") != job["destination"]
            or not E164.fullmatch(job["destination"])
        ):
            await finish({"state": "dead_letter", "error_code": "consent_invalid"})
            return True
        try:
            payload = message_payload(job, self.settings)
        except (ConfigurationError, TypeError, KeyError):
            await finish(
                {"state": "dead_letter", "error_code": "configuration_invalid"}
            )
            return True
        delay = min(3600, 30 * 2 ** (job["attempts"] - 1))
        try:
            response = await self.http.post(
                f"https://graph.facebook.com/{self.settings.api_version}/{self.settings.phone_number_id}/messages",
                headers={"Authorization": f"Bearer {self.settings.access_token}"},
                json=payload,
                timeout=20,
            )
            if response.is_success:
                try:
                    message_id = response.json()["messages"][0]["id"]
                    if not isinstance(message_id, str) or not message_id:
                        raise ValueError()
                except (KeyError, IndexError, ValueError, TypeError):
                    # Ambiguous success: automatic replay could send a duplicate.
                    await finish(
                        {"state": "dead_letter", "error_code": "ambiguous_response"}
                    )
                    return True
                await finish(
                    {
                        "state": "sent",
                        "message_id": message_id,
                        "accepted_at": self.clock(),
                    }
                )
                return True
            retryable = response.status_code == 429 or response.status_code >= 500
            error = (
                f"http_{response.status_code}"  # never persist provider error bodies
            )
            try:
                meta_error = response.json().get("error", {})
                code = meta_error.get("code")
                if isinstance(code, int) and code in {4, 80007, 130429, 131056}:
                    retryable, error = True, f"meta_{code}"
            except (ValueError, AttributeError, TypeError):
                pass
            if response.status_code == 429 or error.startswith("meta_"):
                try:
                    delay = max(delay, float(response.headers.get("Retry-After", "0")))
                except ValueError:
                    try:
                        delay = max(
                            delay,
                            (
                                parsedate_to_datetime(response.headers["Retry-After"])
                                - at
                            ).total_seconds(),
                        )
                    except (ValueError, TypeError, KeyError, OverflowError):
                        pass
                delay = min(delay, 86400)
        except httpx.RequestError:
            retryable, error = True, "transport_error"
        state = (
            "retryable_failure"
            if retryable and job["attempts"] < self.settings.max_attempts
            else "dead_letter"
        )
        await finish(
            {
                "state": state,
                "error_code": error,
                "next_attempt_at": at + timedelta(seconds=delay),
            }
        )
        return True

    async def run(self):
        await self.initialize()
        while True:
            try:
                await self.reconcile()
                await self.apply_receipts()
                busy = await self.process_one()
                await asyncio.sleep(0.1 if busy else 2)
            except asyncio.CancelledError:
                raise
            except Exception:
                # No exception text: HTTP URLs, request headers and DB documents can contain secrets/PII.
                logger.error("whatsapp_worker_cycle_failed")
                await asyncio.sleep(5)


def webhook_router(db_provider, settings_provider=Settings.from_env):
    router = APIRouter(prefix="/webhooks/whatsapp")

    @router.get("")
    async def verify(request: Request):
        settings = settings_provider()
        q = request.query_params
        if (
            not settings.verify_token
            or q.get("hub.mode") != "subscribe"
            or not hmac.compare_digest(
                q.get("hub.verify_token", "").encode(), settings.verify_token.encode()
            )
        ):
            raise HTTPException(403, "Webhook verification failed")
        return PlainTextResponse(q.get("hub.challenge", ""))

    @router.post("")
    async def receive(request: Request):
        settings = settings_provider()
        if not settings.app_secret:
            raise HTTPException(503, "Webhook is not configured")
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 1024 * 1024:
                raise HTTPException(413, "Webhook payload too large")
        expected = (
            "sha256="
            + hmac.new(settings.app_secret.encode(), raw, hashlib.sha256).hexdigest()
        )
        signature = request.headers.get("x-hub-signature-256", "")
        if not hmac.compare_digest(expected.encode(), signature.encode()):
            raise HTTPException(401, "Invalid webhook signature")
        try:
            data = json.loads(raw)
            if data.get("object") != "whatsapp_business_account":
                return {"ok": True}
            receipts = []
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if (
                        value.get("metadata", {}).get("phone_number_id")
                        != settings.phone_number_id
                    ):
                        continue
                    for status in value.get("statuses", []):
                        if status.get("status") not in RANK:
                            continue
                        mid, timestamp = status["id"], str(int(status["timestamp"]))
                        if not isinstance(mid, str) or not mid or len(mid) > 512:
                            raise ValueError()
                        key = hashlib.sha256(
                            f"{mid}:{status['status']}:{timestamp}".encode()
                        ).hexdigest()
                        callback = status.get("biz_opaque_callback_data")
                        receipts.append(
                            {
                                "_id": key,
                                "message_id": mid,
                                "status": status["status"],
                                "timestamp": timestamp,
                                "rank": RANK[status["status"]],
                                "processed": False,
                                "next_check_at": now(),
                                "job_id": (
                                    callback
                                    if isinstance(callback, str) and len(callback) < 200
                                    else None
                                ),
                            }
                        )
        except (ValueError, TypeError, KeyError, AttributeError):
            raise HTTPException(400, "Invalid webhook payload")
        for receipt in receipts:
            try:
                await db_provider().whatsapp_receipts.update_one(
                    {"_id": receipt["_id"]}, {"$setOnInsert": receipt}, upsert=True
                )
            except DuplicateKeyError:
                pass
        # Durable inbox only; processing is independent, and inbound messages never trigger replies.
        return {"ok": True}

    return router
