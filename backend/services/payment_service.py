"""Payment application boundary. Reconciliation records are not charge receipts."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Protocol
from uuid import uuid4

from fastapi import HTTPException

from .repair_facts import money, text_fact
from .payment_repository import PaymentRepository


@dataclass(frozen=True)
class VerifiedBalance:
    amount_due: str
    provider: str
    method: str
    state: str


class PaymentProcessor(Protocol):
    """Adapters verify balances; lifecycle consumers never select a provider."""

    async def verify_balance(
        self, amount_due: str, reference: str
    ) -> VerifiedBalance: ...
    async def verify_receipt(
        self, amount: str, method: str, reference: str
    ) -> dict: ...


class ManualPaymentProcessor:
    async def verify_receipt(self, amount: str, method: str, reference: str) -> dict:
        # Called only after an authorized administrator explicitly confirms receipt.
        return {
            "provider": "manual",
            "amount": amount,
            "method": method,
            "reference": reference,
        }

    async def verify_balance(self, amount_due: str, reference: str) -> VerifiedBalance:
        # An administrator has reconciled this balance externally. Zero does not
        # prove a payment occurred (waivers and corrections are also possible).
        return VerifiedBalance(
            amount_due, "manual", "manual_reconciliation", "BALANCE_VERIFIED"
        )


def verified_balance_summary(repair):
    """Normalize legacy documents at the payment boundary, without rewriting them."""
    summary = repair.get("payment_summary") or {}
    verified = summary.get("balance_state") == "BALANCE_VERIFIED"
    if "balance_state" not in summary:
        verified = summary.get("source") == "manual_reconciliation"
    if (
        not verified
        or summary.get("currency") != "INR"
        or not summary.get("verified_at")
        or not summary.get("verified_by")
    ):
        raise HTTPException(
            400, "An administrator must verify the outstanding payment amount first"
        )
    return {
        "amount_due": format(money(summary.get("amount_due")), ".2f"),
        "currency": "INR",
        "balance_state": "BALANCE_VERIFIED",
    }


class PaymentService:
    """Single-document CAS keeps immutable records and their summary consistent.

    Records represent complete balance attestations, never incremental payments.
    Each record transitions AWAITING_MANUAL_VERIFICATION -> BALANCE_VERIFIED.
    Corrections create new records; no PAID/REFUNDED state is inferred.
    """

    def __init__(
        self,
        repository: PaymentRepository,
        processor: PaymentProcessor,
        notification_factory=None,
    ):
        self.repository = repository
        self.notification_factory = notification_factory
        self.processor = processor

    async def verify_balance(
        self, repair_id, amount_due, reference, actor_id, idempotency_key=None
    ):
        amount = format(money(amount_due), ".2f")
        if not text_fact(reference, 120) or len(reference.strip()) < 3:
            raise HTTPException(400, "A valid reconciliation reference is required")
        reference = reference.strip()
        if not text_fact(actor_id, 200):
            raise HTTPException(400, "A verifier is required")
        payload = json.dumps(
            [repair_id, amount, reference, actor_id], separators=(",", ":")
        )
        fingerprint = sha256(payload.encode()).hexdigest()
        if idempotency_key is not None and not text_fact(idempotency_key, 128):
            raise HTTPException(400, "Invalid idempotency key")
        # Old clients need no new field. Their normalized request is replay-safe.
        key = idempotency_key or "legacy:" + fingerprint
        for _ in range(3):
            repair = await self.repository.get(repair_id)
            if not repair:
                raise HTTPException(404, "Repair request not found")
            records = repair.get("payment_records", [])
            for record in records:
                if record["idempotency_key"] == key:
                    if record["request_fingerprint"] != fingerprint:
                        raise HTTPException(
                            409, "Idempotency key already used for another request"
                        )
                    return {"ok": True}
            if repair.get("payment_receipt"):
                raise HTTPException(
                    409,
                    "Verified receipt is immutable; balance corrections require review",
                )
            if repair["status"] not in ("REPAIR_COMPLETED", "PAYMENT_PENDING"):
                raise HTTPException(
                    400, "Verify the final balance after repair completion"
                )
            # Bound embedded history well below Mongo's document limit; never truncate audit.
            if len(records) >= 500:
                raise HTTPException(
                    409, "Payment reconciliation history requires administrator review"
                )
            balance = await self.processor.verify_balance(amount, reference)
            if (
                balance.amount_due != amount
                or balance.state != "BALANCE_VERIFIED"
                or not text_fact(balance.provider)
                or not text_fact(balance.method)
            ):
                raise HTTPException(400, "Invalid verified balance")
            timestamp = datetime.now(timezone.utc).isoformat()
            record_id = "pay_" + uuid4().hex
            record = {
                "id": record_id,
                "repair_id": repair_id,
                "currency": "INR",
                "amount_due": amount,
                "verified_amount": amount,
                "verified_amount_kind": "outstanding_balance",
                "provider": balance.provider,
                "method": balance.method,
                "provider_reference": reference,
                "state": balance.state,
                "created_at": timestamp,
                "verified_at": timestamp,
                "audit": {
                    "verified_by": actor_id,
                    "supersedes": records[-1]["id"] if records else None,
                    "legacy_summary": (
                        repair.get("payment_summary") if not records else None
                    ),
                },
                "transitions": [
                    {
                        "from": "AWAITING_MANUAL_VERIFICATION",
                        "to": balance.state,
                        "at": timestamp,
                        "actor_id": actor_id,
                    }
                ],
                "idempotency_key": key,
                "request_fingerprint": fingerprint,
            }
            summary = {
                "amount_due": float(money(amount)),
                "currency": "INR",
                "source": balance.method,
                "balance_state": balance.state,
                "payment_record_id": record_id,
                "state": "PENDING" if money(amount) > 0 else "BALANCE_CLEARED",
                "verified_by": actor_id,
                "verified_at": timestamp,
                "reference": reference,
            }
            committed = await self.repository.commit(
                repair,
                {"payment_summary": summary, "updated_at": timestamp},
                {"payment_records": record},
            )
            if committed:
                return {"ok": True}
            # Only replay an identical winning operation. Never overwrite a new balance.
            latest = await self.repository.get(repair_id)
            if not any(
                r["idempotency_key"] == key
                for r in (latest or {}).get("payment_records", [])
            ):
                raise HTTPException(409, "Repair changed; refresh and try again")
        raise HTTPException(409, "Repair changed; refresh and try again")

    async def submit_reference(self, repair_id, reference, actor_id):
        if not text_fact(reference, 120) or len(reference.strip()) < 3:
            raise HTTPException(400, "A valid transaction reference is required")
        repair = await self.repository.get(repair_id)
        if not repair:
            raise HTTPException(404, "Repair request not found")
        if repair["user_id"] != actor_id:
            raise HTTPException(
                403, "Only the repair customer can submit payment evidence"
            )
        if (
            repair.get("payment_receipt")
            or money(verified_balance_summary(repair)["amount_due"]) <= 0
        ):
            raise HTTPException(409, "No outstanding balance")
        evidence = repair.get("payment_evidence", [])
        reference = reference.strip()
        if any(item["reference"] == reference for item in evidence):
            return {"ok": True, "state": "AWAITING_MANUAL_VERIFICATION"}
        if len(evidence) >= 20:
            raise HTTPException(
                409, "Please contact support to review existing references"
            )
        timestamp = datetime.now(timezone.utc).isoformat()
        if not await self.repository.commit(
            repair,
            {
                "payment_summary.state": "AWAITING_MANUAL_VERIFICATION",
                "updated_at": timestamp,
            },
            {
                "payment_evidence": {
                    "reference": reference,
                    "submitted_by": actor_id,
                    "submitted_at": timestamp,
                    "verified": False,
                }
            },
        ):
            raise HTTPException(409, "Repair changed; refresh and try again")
        return {"ok": True, "state": "AWAITING_MANUAL_VERIFICATION"}

    async def receive(
        self,
        repair_id,
        amount,
        method,
        reference,
        actor_id,
        idempotency_key,
        funds_received,
        customer=None,
    ):
        import re

        if funds_received is not True:
            raise HTTPException(400, "Confirm funds reached the merchant account")
        if not text_fact(actor_id, 200) or not text_fact(idempotency_key, 128):
            raise HTTPException(400, "Verifier and idempotency key are required")
        raw_amount = money(amount)
        if raw_amount <= 0 or str(amount).strip().lower() in ("true", "false"):
            raise HTTPException(400, "Payment amount must be positive")
        # Do not silently round a receipt with fractional paise.
        from decimal import Decimal

        if Decimal(str(amount)) != raw_amount:
            raise HTTPException(
                400, "Payment amounts support at most two decimal places"
            )
        amount = format(raw_amount, ".2f")
        if method not in ("upi", "bank_transfer", "cash"):
            raise HTTPException(400, "Unsupported manual payment method")
        if method == "cash":
            if reference:
                raise HTTPException(400, "Cash receipt IDs are generated by RushX")
            reference = (
                "CASH-"
                + sha256(f"{repair_id}:{idempotency_key}".encode())
                .hexdigest()[:24]
                .upper()
            )
        else:
            reference = (reference or "").strip().upper()
            if not re.fullmatch(
                r"[A-Z0-9][A-Z0-9-]{5,119}", reference
            ) or reference.startswith("CASH-"):
                raise HTTPException(
                    400, "A valid electronic transaction reference is required"
                )
        fingerprint = sha256(
            json.dumps(
                [repair_id, amount, method, reference, actor_id, idempotency_key]
            ).encode()
        ).hexdigest()
        repair = await self.repository.get(repair_id)
        if not repair:
            raise HTTPException(404, "Repair request not found")
        receipt = repair.get("payment_receipt")
        if receipt:
            if receipt["request_fingerprint"] == fingerprint:
                await self.repository.applied(reference)
                return {"ok": True, "payment_id": receipt["id"], "state": "PAID"}
            raise HTTPException(409, "Payment already verified")
        if repair["status"] not in (
            "PAYMENT_PENDING",
            "READY_TO_SHIP",
            "SHIPPED_TO_CUSTOMER",
            "DELIVERED",
            "COMPLETED",
        ):
            raise HTTPException(
                409, "Move the repair to PAYMENT_PENDING before recording receipt"
            )
        due = verified_balance_summary(repair)["amount_due"]
        if due != amount:
            raise HTTPException(
                400,
                "Payment must equal the outstanding balance; partial payments and overpayment are not supported",
            )
        verified = await self.processor.verify_receipt(amount, method, reference)
        if (
            verified.get("amount") != amount
            or verified.get("reference") != reference
            or verified.get("method") != method
            or not text_fact(verified.get("provider"))
        ):
            raise HTTPException(400, "Invalid verified receipt")
        timestamp = datetime.now(timezone.utc).isoformat()
        payment_id = "pay_" + uuid4().hex
        safe_reference = "REF-" + reference[-4:]
        receipt = {
            "id": payment_id,
            "repair_id": repair_id,
            "currency": "INR",
            "amount_due": "0.00",
            "verified_amount": amount,
            "method": method,
            "provider": verified["provider"],
            "provider_reference": reference,
            "safe_reference": safe_reference,
            "state": "PAID",
            "created_at": timestamp,
            "verified_at": timestamp,
            "verified_by": actor_id,
            "idempotency_key": idempotency_key,
            "request_fingerprint": fingerprint,
            "audit": {"funds_received_confirmed": True, "verified_by": actor_id},
            "transitions": [
                {
                    "from": (repair.get("payment_summary") or {}).get(
                        "state", "PENDING"
                    ),
                    "to": "PAID",
                    "at": timestamp,
                    "actor_id": actor_id,
                }
            ],
        }
        event = {
            "id": payment_id + ":received",
            "type": "PaymentReceived",
            "repair_id": repair_id,
            "payment_id": payment_id,
            "currency": "INR",
            "verified_amount": amount,
            "safe_reference": safe_reference,
            "occurred_at": timestamp,
        }
        operation = await self.repository.reserve(
            reference,
            {
                "repair_id": repair_id,
                "fingerprint": fingerprint,
                "receipt": receipt,
                "event": event,
                "expected_revision": repair.get("revision"),
                "created_at": timestamp,
            },
        )
        receipt, event = operation["receipt"], operation["event"]
        # Revalidate current balance/state on every retry above, then CAS the
        # fresh aggregate. Unrelated edits cannot strand a valid reservation.
        summary = {
            **repair["payment_summary"],
            "amount_due": 0.0,
            "balance_state": "BALANCE_VERIFIED",
            "state": "PAID",
            "verified_at": receipt["verified_at"],
            "verified_by": actor_id,
            "payment_record_id": receipt["id"],
        }
        pushes = {"payment_events": event}
        if self.notification_factory:
            notification = self.notification_factory(repair, event, customer)
            if notification:
                pushes["whatsapp_outbox"] = notification
        committed = await self.repository.commit(
            repair,
            {
                "payment_receipt": receipt,
                "payment_summary": summary,
                "updated_at": receipt["verified_at"],
            },
            pushes,
        )
        if not committed:
            latest = await self.repository.get(repair_id)
            if (latest.get("payment_receipt") or {}).get(
                "request_fingerprint"
            ) != fingerprint:
                raise HTTPException(
                    409, "Repair changed; reserved verification needs reconciliation"
                )
        await self.repository.applied(reference)
        return {"ok": True, "payment_id": receipt["id"], "state": "PAID"}
