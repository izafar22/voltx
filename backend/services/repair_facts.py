"""Validated repair facts shared by business transitions and notification snapshots."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import HTTPException

MONEY_FIELDS = (
    "labor",
    "diagnostic_fee",
    "incoming_logistics_cost",
    "return_shipping_cost",
    "other_charges",
    "tax",
)


def money(value):
    try:
        if isinstance(value, bool) or value is None:
            raise ValueError()
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > Decimal("99999999.99"):
            raise ValueError()
        return amount.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(
            400, "A valid non-negative INR amount is required"
        ) from None


def text_fact(value, limit=256):
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value) <= limit
        and not any(ord(c) < 32 for c in value)
    )


def calculated_estimate(estimate):
    if not isinstance(estimate, dict):
        raise HTTPException(400, "A persisted valid estimate is required")
    parts = estimate.get("parts", [])
    if not isinstance(parts, list):
        raise HTTPException(400, "Invalid estimate parts")
    total = Decimal(0)
    for part in parts:
        if (
            not isinstance(part, dict)
            or type(part.get("qty", 1)) is not int
            or not 1 <= part.get("qty", 1) <= 10000
        ):
            raise HTTPException(400, "Invalid estimate quantity")
        total += money(part.get("price", 0)) * part.get("qty", 1)
    for key in MONEY_FIELDS:
        total += money(estimate.get(key, 0))
    return money(total)


def estimate_total(repair, published=False):
    estimate = repair.get("estimate")
    computed = calculated_estimate(estimate)
    if "total" not in estimate or money(estimate["total"]) != computed:
        raise HTTPException(
            400, "Persisted estimate total is invalid; review the estimate"
        )
    if published and estimate.get("status") not in ("SENT", "APPROVED", "DECLINED"):
        raise HTTPException(400, "A published estimate is required")
    return format(computed, ".2f")


def amount_due(repair):
    payment = repair.get("payment_summary") or {}
    if (
        payment.get("source") != "manual_reconciliation"
        or payment.get("currency") != "INR"
        or not payment.get("verified_at")
        or not payment.get("verified_by")
    ):
        raise HTTPException(
            400, "An administrator must verify the outstanding payment amount first"
        )
    due = money(payment.get("amount_due"))
    if due <= 0:
        raise HTTPException(
            400, "Payment pending requires a positive verified amount due"
        )
    return format(due, ".2f")


def shipment_details(repair):
    shipment = repair.get("return_shipment") or {}
    if (
        not text_fact(shipment.get("courier"), 128)
        or not text_fact(shipment.get("tracking_number"), 128)
        or not shipment.get("confirmed_by")
        or not shipment.get("confirmed_at")
    ):
        raise HTTPException(
            400, "Confirmed return courier and tracking details are required"
        )
    return {k: shipment[k].strip() for k in ("courier", "tracking_number")}


def validate_transition_facts(repair, status):
    if status == "ESTIMATE_SENT":
        estimate_total(repair)
    elif status in ("CUSTOMER_APPROVED", "CUSTOMER_DECLINED"):
        estimate_total(repair, published=True)
    elif status == "PAYMENT_PENDING":
        amount_due(repair)
    elif status == "SHIPPED_TO_CUSTOMER":
        shipment_details(repair)
