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
from pathlib import Path
from urllib.parse import unquote

from .payment_config import public_payment_instructions, valid_public_qr_url
from .repair_facts import estimate_total, amount_due, shipment_details, text_fact

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)
E164 = re.compile(r"\+[1-9][0-9]{7,14}\Z")
# Catalog is a reviewed schema and submission artifact, never an approval claim.
CATALOG = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "whatsapp_utility_catalog.json"
    ).read_text()
)
STATUS_TEXT = {status: template["body"] for status, template in CATALOG.items()}
SCHEMA_VERSION = 2
RANK = {"sent": 1, "failed": 2, "delivered": 3, "read": 4}


class WebhookAccessLogFilter(logging.Filter):
    """Uvicorn access logging must not record Meta's verification-token query."""

    def filter(self, record):
        args = record.args
        if isinstance(args, tuple) and len(args) == 5 and isinstance(args[2], str):
            path = args[2]
            if path.split("?", 1)[0].rstrip(
                "/"
            ) == "/api/webhooks/whatsapp" or "hub.verify_token=" in unquote(path):
                record.args = (*args[:2], path.split("?", 1)[0], *args[3:])
        return True


def now():
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Settings:
    enabled: bool = False
    access_token: str = field(default="", repr=False)
    phone_number_id: str = field(default="", repr=False)
    test_phone_number_id: str = field(default="", repr=False)
    production_approved: bool = False
    verify_token: str = field(default="", repr=False)
    app_secret: str = field(default="", repr=False)
    api_version: str = ""
    dispatch_address: str = field(default="", repr=False)
    templates: dict = field(default_factory=dict, repr=False)
    mode: str = "test"
    test_recipients: tuple = field(default=(), repr=False)
    max_attempts: int = 5
    payment_qr_url: str = ""

    @classmethod
    def from_env(cls):
        # Invalid configuration must not break existing repair routes.
        try:
            templates = json.loads(os.getenv("WHATSAPP_TEMPLATES_JSON", "{}"))
        except (TypeError, ValueError):
            templates = {}
        return cls(
            payment_qr_url=public_payment_instructions()["qr_image_url"] or "",
            enabled=os.getenv("WHATSAPP_ENABLED", "false").lower() == "true",
            access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
            phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
            test_phone_number_id=os.getenv("WHATSAPP_TEST_PHONE_NUMBER_ID", ""),
            production_approved=os.getenv(
                "WHATSAPP_PRODUCTION_APPROVED", "false"
            ).lower()
            == "true",
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


def event_for(repair, status, event_id, settings, customer=None, payment_event=None):
    consent = repair.get("whatsapp_consent", {})
    if (
        not settings.enabled
        or consent.get("opted_in") is not True
        or status not in CATALOG
    ):
        return None
    values = {
        "customer_name": (customer or {}).get("name", ""),
        "repair_number": repair["repair_request_number"],
    }
    if status == "REQUESTED":
        info = repair.get("charger_info") or {}
        values["charger_description"] = " ".join(
            str(info[k]).strip() for k in ("brand", "model") if info.get(k)
        )
    elif status == "AWAITING_SHIPMENT":
        values["dispatch_address"] = settings.dispatch_address
    elif status == "ESTIMATE_SENT":
        values["estimate_total"] = estimate_total(repair)
    elif status == "PAYMENT_PENDING":
        values["amount_due"] = amount_due(repair)
    elif status == "PAYMENT_RECEIVED":
        if not payment_event or payment_event.get("type") != "PaymentReceived":
            return None
        values.update(
            {key: payment_event[key] for key in ("verified_amount", "safe_reference")}
        )
    elif status == "SHIPPED_TO_CUSTOMER":
        values.update(shipment_details(repair))
    event = {
        "_id": (
            f"{repair['id']}:REQUESTED"
            if status == "REQUESTED"
            else f"{repair['id']}:{event_id}"
        ),
        "repair_id": repair["id"],
        "event_id": event_id,
        "status": status,
        "schema_version": SCHEMA_VERSION,
        "delivery_scope": {
            "mode": settings.mode,
            "phone_number_id": settings.phone_number_id,
        },
        "destination": consent.get("destination", ""),
        "consent_at": consent.get("at"),
        "values": values,
    }

    if status == "PAYMENT_PENDING" and settings.payment_qr_url:
        try:
            configured_template("PAYMENT_PENDING_QR", settings)
            event["template_key"] = "PAYMENT_PENDING_QR"
            event["qr_image_url"] = settings.payment_qr_url
        except ConfigurationError:
            pass  # Unapproved optional media must not replace the existing text template.
    return event


def payment_received_notification(repair, event, settings, customer=None):
    return event_for(
        repair,
        "PAYMENT_RECEIVED",
        event["id"],
        settings,
        customer=customer,
        payment_event=event,
    )


class ConfigurationError(Exception):
    pass


class SnapshotError(Exception):
    pass


def configured_template(status, settings):
    template = (
        settings.templates.get(status) if isinstance(settings.templates, dict) else None
    )
    catalog_status = "PAYMENT_PENDING" if status == "PAYMENT_PENDING_QR" else status
    if not isinstance(template, dict) or catalog_status not in CATALOG:
        raise ConfigurationError()
    name = template.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9_]{1,512}", name):
        raise ConfigurationError()
    sandbox = (
        settings.mode == "test"
        and name == "hello_world"
        and template.get("parameters") == []
    )
    if template.get("language") != "en_US":
        raise ConfigurationError()
    if not sandbox and (
        name == "hello_world"
        or template.get("parameters") != CATALOG[catalog_status]["parameters"]
        or template.get("approval_status") != "approved"
        or template.get("category") != "UTILITY"
    ):
        raise ConfigurationError()
    pending_template = settings.templates.get("PAYMENT_PENDING")
    pending_name = (
        pending_template.get("name") if isinstance(pending_template, dict) else None
    )
    if status == "PAYMENT_PENDING_QR" and (
        sandbox
        or template.get("header_format") != "IMAGE"
        or name == CATALOG["PAYMENT_PENDING"]["name"]
        or name == pending_name
    ):
        raise ConfigurationError()
    return template


def validate_settings(settings):
    if (
        not settings.access_token
        or not re.fullmatch(r"[0-9]+", settings.phone_number_id)
        or not re.fullmatch(r"v[0-9]+\.[0-9]+", settings.api_version)
        or not settings.app_secret
        or not settings.verify_token
        or not re.fullmatch(r"[0-9]+", settings.test_phone_number_id)
    ):
        raise ConfigurationError()
    if settings.mode == "test":
        if (
            settings.phone_number_id != settings.test_phone_number_id
            or not settings.test_recipients
        ):
            raise ConfigurationError()
        if any(
            not isinstance(p, str) or not E164.fullmatch(p)
            for p in settings.test_recipients
        ):
            raise ConfigurationError()
    elif settings.mode == "production":
        if (
            not settings.production_approved
            or settings.phone_number_id == settings.test_phone_number_id
        ):
            raise ConfigurationError()
        for status in CATALOG:
            if status != "PAYMENT_RECEIVED":
                configured_template(status, settings)
    else:
        raise ConfigurationError()


def message_payload(job, settings):
    validate_settings(settings)
    if (
        job.get("schema_version") != SCHEMA_VERSION
        or job.get("status") not in CATALOG
        or job.get("delivery_scope")
        != {"mode": settings.mode, "phone_number_id": settings.phone_number_id}
    ):
        raise SnapshotError()
    destination = job.get("destination")
    if not isinstance(destination, str) or not E164.fullmatch(destination):
        raise SnapshotError()
    if settings.mode == "test" and destination not in settings.test_recipients:
        raise ConfigurationError()
    template_key = job.get("template_key", job["status"])
    if template_key != job["status"] and not (
        job["status"] == "PAYMENT_PENDING" and template_key == "PAYMENT_PENDING_QR"
    ):
        raise SnapshotError()
    template = configured_template(template_key, settings)
    params = template["parameters"]
    values = job.get("values", {})
    # Validate the entire schema even for hello_world: it cannot bypass missing business facts.
    if not isinstance(values, dict) or set(values) != set(
        CATALOG[job["status"]]["parameters"]
    ):
        raise SnapshotError()
    if any(not text_fact(value, 1024) for value in values.values()):
        raise SnapshotError()
    for key in ("amount_due", "estimate_total", "verified_amount"):
        if key in values and not re.fullmatch(r"[0-9]{1,8}\.[0-9]{2}", values[key]):
            raise SnapshotError()
    if any(
        key in values and float(values[key]) <= 0
        for key in ("amount_due", "verified_amount")
    ):
        raise SnapshotError()
    body = {"name": template["name"], "language": {"code": template["language"]}}
    if params:
        body["components"] = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": values[p]} for p in params],
            }
        ]
    if template_key == "PAYMENT_PENDING_QR":
        url = job.get("qr_image_url", "")
        if url != settings.payment_qr_url or not valid_public_qr_url(url):
            raise ConfigurationError()
        body["components"].insert(
            0,
            {
                "type": "header",
                "parameters": [{"type": "image", "image": {"link": url}}],
            },
        )
    return {
        "messaging_product": "whatsapp",
        "to": destination,
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
        await self.db.whatsapp_jobs.create_index([("state", 1), ("lease_until", 1)])
        await self.db.whatsapp_jobs.create_index([("error_code", 1), ("updated_at", 1)])
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
            if receipt.get("phone_number_id"):
                query = {
                    "$and": [
                        query,
                        {
                            "$or": [
                                {
                                    "delivery_scope.phone_number_id": receipt[
                                        "phone_number_id"
                                    ]
                                },
                                {"schema_version": {"$exists": False}},
                            ]
                        },
                    ]
                }
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

    async def metrics(self):
        at = self.clock()
        states = (
            "pending",
            "processing",
            "retryable_failure",
            "sent",
            "delivered",
            "read",
            "failed",
            "dead_letter",
        )
        counts = {
            state: await self.db.whatsapp_jobs.count_documents({"state": state})
            for state in states
        }
        oldest = await self.db.whatsapp_jobs.find_one(
            {"state": {"$in": ["pending", "retryable_failure"]}},
            sort=[("created_at", 1)],
        )
        created = (oldest or {}).get("created_at", at)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        lag = max(0, int((at - created).total_seconds()))
        expired = await self.db.whatsapp_jobs.count_documents(
            {"state": "processing", "lease_until": {"$lt": at}}
        )
        missing = await self.db.whatsapp_jobs.count_documents(
            {"state": "sent", "accepted_at": {"$lt": at - timedelta(hours=1)}}
        )
        throttled = await self.db.whatsapp_jobs.count_documents(
            {
                "error_code": {
                    "$in": [
                        "http_429",
                        "meta_4",
                        "meta_80007",
                        "meta_130429",
                        "meta_131056",
                    ]
                },
                "updated_at": {"$gte": at - timedelta(hours=1)},
            }
        )
        configuration = await self.db.whatsapp_jobs.count_documents(
            {"state": "dead_letter", "error_code": "configuration_invalid"}
        )
        return {
            "counts": counts,
            "oldest_pending_seconds": lag,
            "expired_leases": expired,
            "missing_receipts_over_one_hour": missing,
            "throttled_jobs_last_hour": throttled,
            "invalid_configuration_jobs": configuration,
            "outbox_repairs": await self.db.repair_requests.count_documents(
                {"whatsapp_outbox._id": {"$exists": True}}
            ),
            "unprocessed_receipts": await self.db.whatsapp_receipts.count_documents(
                {"processed": False}
            ),
            "alerts": {
                "pending_lag": lag > 300,
                "dead_letters": counts["dead_letter"] > 0,
                "stuck_leases": expired > 0,
                "missing_receipts": missing > 0,
                "provider_throttling": throttled >= 5,
                "invalid_configuration": configuration > 0,
            },
        }

    async def safe_requeue(self, job_id):
        job = await self.db.whatsapp_jobs.find_one({"_id": job_id})
        allowed = {
            "configuration_invalid",
            "transport_error",
            "attempts_exhausted",
            "http_429",
            "http_500",
            "http_502",
            "http_503",
            "http_504",
            "meta_4",
            "meta_80007",
            "meta_130429",
            "meta_131056",
        }
        if not job:
            raise HTTPException(404, "Notification job not found")
        if (
            job["state"] != "dead_letter"
            or job.get("error_code") not in allowed
            or job.get("message_id")
            or job.get("accepted_at")
            or job.get("dispatch_started_at")
            or job.get("delivery_rank", 0) > 0
        ):
            raise HTTPException(409, "This job cannot be safely replayed")
        try:
            message_payload(job, self.settings)
        except (ConfigurationError, SnapshotError, TypeError, KeyError):
            raise HTTPException(
                409,
                "Correct configuration before retrying; snapshots cannot be rewritten",
            ) from None
        repair = await self.db.repair_requests.find_one({"id": job["repair_id"]})
        consent = (repair or {}).get("whatsapp_consent", {})
        if (
            consent.get("opted_in") is not True
            or consent.get("at") != job.get("consent_at")
            or consent.get("destination") != job.get("destination")
        ):
            raise HTTPException(409, "Consent is not valid")
        result = await self.db.whatsapp_jobs.update_one(
            {
                "_id": job_id,
                "state": "dead_letter",
                "error_code": job["error_code"],
                "attempts": job["attempts"],
                "message_id": None,
                "accepted_at": None,
                "dispatch_started_at": None,
                "delivery_rank": 0,
            },
            {
                "$set": {
                    "state": "pending",
                    "attempts": 0,
                    "next_attempt_at": self.clock(),
                    "updated_at": self.clock(),
                },
                "$inc": {"manual_replays": 1},
                "$unset": {"error_code": ""},
            },
        )
        if not result.modified_count:
            raise HTTPException(409, "Job changed; refresh and review")

    async def process_one(self):
        if not self.settings.enabled:
            return False
        at, lease = self.clock(), uuid.uuid4().hex
        sender = hashlib.sha256(
            f"{self.settings.mode}:{self.settings.phone_number_id}".encode()
        ).hexdigest()
        if await self.db.whatsapp_control.find_one(
            {"_id": sender, "paused_until": {"$gt": at}}
        ):
            return False
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
            sort=[("next_attempt_at", 1), ("created_at", 1)],
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

        if job.get("dispatch_started_at"):
            await finish({"state": "dead_letter", "error_code": "ambiguous_delivery"})
            return True
        if job["attempts"] > self.settings.max_attempts:
            await finish({"state": "dead_letter", "error_code": "attempts_exhausted"})
            return True
        repair = await self.db.repair_requests.find_one(
            {"id": job["repair_id"]}, {"whatsapp_consent": 1, "payment_summary": 1}
        )
        consent = (repair or {}).get("whatsapp_consent", {})
        if (
            consent.get("opted_in") is not True
            or consent.get("at") != job.get("consent_at")
            or consent.get("source") != "repair_submission_v1"
            or consent.get("destination") != job["destination"]
            or not isinstance(job.get("destination"), str)
            or not E164.fullmatch(job["destination"])
        ):
            await finish({"state": "dead_letter", "error_code": "consent_invalid"})
            return True
        if job["status"] == "PAYMENT_PENDING":
            try:
                if amount_due(repair or {}) != job.get("values", {}).get("amount_due"):
                    raise HTTPException(400, "Balance changed")
            except HTTPException:
                await finish(
                    {"state": "dead_letter", "error_code": "business_facts_changed"}
                )
                return True
        try:
            payload = message_payload(job, self.settings)
        except SnapshotError:
            await finish({"state": "dead_letter", "error_code": "snapshot_invalid"})
            return True
        except (ConfigurationError, TypeError, KeyError):
            await finish(
                {"state": "dead_letter", "error_code": "configuration_invalid"}
            )
            return True
        delay = min(3600, 30 * 2 ** (job["attempts"] - 1))
        # Fenced durable send-intent marker. If persistence fails, no request is made.
        marked = await self.db.whatsapp_jobs.update_one(
            claim, {"$set": {"dispatch_started_at": self.clock()}}
        )
        if not marked.modified_count:
            return True
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
                await self.db.whatsapp_control.update_one(
                    {"_id": sender},
                    {"$max": {"paused_until": at + timedelta(seconds=delay)}},
                    upsert=True,
                )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            retryable, error = True, "transport_error"
        except httpx.RequestError:
            await finish({"state": "dead_letter", "error_code": "ambiguous_delivery"})
            return True
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
                "dispatch_started_at": None,
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
        if not settings.app_secret or not settings.phone_number_id:
            raise HTTPException(503, "Webhook is not configured")
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > 1024 * 1024:
                raise HTTPException(413, "Webhook payload too large")
            raw.extend(chunk)
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
                        mid, timestamp = status["id"], status["timestamp"]
                        if (
                            isinstance(timestamp, bool)
                            or not isinstance(timestamp, (str, int))
                            or not re.fullmatch(r"[0-9]{1,12}", str(timestamp))
                        ):
                            raise ValueError()
                        timestamp = str(int(timestamp))
                        if not isinstance(mid, str) or not mid or len(mid) > 512:
                            raise ValueError()
                        key = hashlib.sha256(
                            f"{mid}:{status['status']}:{timestamp}".encode()
                        ).hexdigest()
                        callback = status.get("biz_opaque_callback_data")
                        if len(receipts) >= 100:
                            raise HTTPException(413, "Too many webhook statuses")
                        receipts.append(
                            {
                                "_id": key,
                                "message_id": mid,
                                "status": status["status"],
                                "timestamp": timestamp,
                                "phone_number_id": settings.phone_number_id,
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
