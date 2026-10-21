# RushX manual payments

PR #4 payment follow-ups add an explicit **receipt verification** workflow alongside
the existing balance reconciliation API. No gateway, payment links, automatic
charges, refunds or partial receipt allocation is implemented. No real payment is
created by these APIs: administrators attest to money received outside RushX.

## Boundaries and records

- `PaymentService` owns validation, idempotency, balance/evidence/receipt use cases,
  amount matching and domain events. It accepts `PaymentProcessor` and
  `PaymentRepository` ports; it does not import WhatsApp or call HTTP.
- `ManualPaymentProcessor` is the only production-wired strategy. Admin receipt
  confirmation is mandatory. A future adapter must authenticate and verify its
  provider's signed webhook, deduplicate provider events, normalize a verified
  receipt and invoke the same application boundary. Never expose the manual
  endpoint as an unauthenticated webhook. No speculative gateway endpoints exist.
- `MongoPaymentRepository` owns reference reservation and aggregate CAS. Money is
  calculated as Decimal; immutable records use two-decimal INR strings. The old
  numeric `payment_summary.amount_due` response remains compatible.
- Each balance reconciliation creates an immutable `payment_records` item with
  repair ID, provider/method, reference, verifier, timestamps, idempotency key and
  transition history. Its `verified_amount_kind=outstanding_balance` explicitly
  distinguishes a balance attestation from a money receipt.
- A successful receipt creates immutable `payment_receipt` and `PaymentReceived`
  domain event records. The injected WhatsApp adapter turns the neutral event
  into the existing durable notification outbox. All are saved in one CAS write,
  together with the zero balance and `PAID` state. Repair lifecycle status never
  changes automatically. There are no cross-document settlement transactions.

## Operator and customer workflow

1. After repair completion, use the existing **Verify outstanding payment** form
   to record the authoritative remaining amount (including any payments reconciled
   externally before this system). This is not a new charge or receipt.
2. Move the repair to `PAYMENT_PENDING`. The existing approved text template
   requests the verified positive balance; optional reviewed QR configuration can
   select a separately approved media template. Consent is required for WhatsApp.
3. The customer can see instructions and an optional merchant QR in their repair
   dashboard. They may submit a reference, marked **unverified evidence**. Evidence
   does not reduce the balance, create a receipt or enqueue an acknowledgement.
4. Check the merchant account (or cash physically received), then use **Verify
   payment received**. Enter the exact remaining amount, choose UPI, bank transfer
   or cash, enter the electronic UTR, and explicitly confirm receipt. The server
   generates cash receipt IDs. Verifier and verification time are server-owned.
5. A full verified receipt changes payment state to `PAID` and may enqueue a
   separate acknowledgement. Continue existing repair shipping statuses normally.

Payment states: `UNVERIFIED` -> `PENDING` after positive balance verification;
`PENDING` -> `AWAITING_MANUAL_VERIFICATION` on evidence; either pending state ->
`PAID` only on full authoritative receipt. A zero balance reconciliation means
`BALANCE_CLEARED`, **not PAID**: it could reflect a waiver. Balance audit records
track `AWAITING_MANUAL_VERIFICATION` -> `BALANCE_VERIFIED` separately from settlement.
Corrections before receipt create a new audit record and can restore `PENDING`.
Receipts are immutable; refund, reversal, reopening paid balances and partial
receipts are not supported. They require a separately reviewed business workflow.
Recording a receipt requires `PAYMENT_PENDING` or a later normal shipping/completed
stage, so early settlement cannot strand the existing lifecycle at repair completion.

These are intentional additions authorized by the second payment review comment:
customer evidence and QR display, an explicit admin receipt form, an immutable paid
state, and a ninth notification. Existing balance inputs/response and the eight
repair transitions remain supported. Balance editing after an actual receipt is
blocked to protect the audit trail. No estimate total is substituted for the
admin-reconciled remaining balance. A receipt below or above that amount is rejected;
there is no implicit allocation of partial payments or overpayment.

## Stable APIs and authorization

All endpoints use existing cookie authentication and trusted-origin protections.

| API under `/api/repairs/{id}` | Access | Purpose |
| --- | --- | --- |
| `PATCH /payment` | Admin | Existing `{amount_due, reference}`, optional `idempotency_key`; returns `{ok:true}` |
| `GET /payment` | Repair customer or admin | Neutral state, balance, safe receipt and public instructions; admin additionally receives evidence/audit |
| `POST /payment/reference` | Repair customer only | `{reference}`; unverified evidence, max 20 distinct submissions |
| `POST /payment/verify` | Admin only | `{amount, method, reference, funds_received:true, idempotency_key}`; returns `{ok:true,payment_id,state:"PAID"}` |

Electronic references are normalized to uppercase and accept 6–120 ASCII letters,
digits/hyphens. Their hashed uniqueness key is scoped to the one RushX merchant
ledger across all repairs **and electronic methods** (a UTR cannot be reused as a
bank transfer). Cash references are server-generated in a disjoint `CASH-` namespace.
Full references are admin-only; notifications and customer receipts use `REF-` plus
the last four characters. No card data, banking credentials or merchant secret is
stored. A single repair can have one full receipt. Duplicate identical requests
return the original result; conflicting requests return 409. Old balance clients
get deterministic request fingerprints without adding a required field. To make a
new, deliberate reconciliation of previously used identical balance/reference data,
use a fresh explicit idempotency key (or a new descriptive reconciliation reference).

## Durability, concurrency and recovery

Mongo's built-in unique `_id` on `payment_references` atomically reserves a normalized
reference before settlement. A compound unique index on repair ID and receipt
idempotency key also prevents changing inputs after a failed reservation. The
repository creates this index before reserving; the API database role needs index
creation permission on `payment_references` (or provision this named index ahead
of time: `repair_payment_idempotency`). A reservation contains the intended immutable receipt,
domain event, request fingerprint and original revision; `RESERVED` is **not PAID**.
The repair aggregate is authoritative: payment receipt, zero balance, event and
notification outbox are committed together using status/revision CAS. After that,
the reservation becomes `APPLIED`. Workers materialize outbox jobs idempotently and
retain the existing retry, lease, consent recheck and ambiguous-send safeguards.
A paid balance also invalidates any still-unsent pending-payment request.

If interrupted before aggregate commit, repeat the exact verification request with
the same key, actor and inputs. It rechecks the current balance/state/consent and
CASes the current revision. If interrupted after commit, the same retry returns the
existing receipt, repairs the reservation marker, and emits no second event. A
conflicting CAS returns 409; it never overwrites another receipt or balance.

Operational reconciliation: inspect `payment_references` where `state=RESERVED`
and compare each `repair_id` / receipt fingerprint to the authoritative repair.
If a matching receipt exists, an exact retry marks it APPLIED. If none exists,
retry only after verifying that the reserved amount/reference still represents
real funds. Changed amount, cancelled repair, different actor/key or reused UTR
fails closed. Escalate conflicting/abandoned reservations for an audited manual
review; **do not delete or release reservations automatically**, nor mark PAID from
reservation data. There is deliberately no automatic collection/retry of payments.
Back up both collections together. Bound balance audit history to 500 records;
exhaustion returns 409 and requires operator review rather than silently truncating.

## Optional QR and new template setup

Default: no QR configured; existing text-only `rushx_payment_pending_v1` unchanged.
Set `RUSHX_UPI_QR_IMAGE_URL` to a stable public HTTPS image of the **RushX-owned merchant**
QR and `RUSHX_UPI_QR_REVIEWED=true` only after an operator has checked the merchant
identity, decoded QR and destination account. No personal QR, tokens, query strings,
embedded credentials or dynamic customer-supplied URLs. The application does not
fetch, generate or verify the QR's account ownership. Host an immutable, reviewed
image asset with appropriate access controls; never repoint it to a different payee.
The reviewed URL displays in the authenticated dashboard. No extra QR library needed.

For WhatsApp QR, submit a **new** Utility template `rushx_payment_pending_qr_v1`,
`en_US`, IMAGE header, and the existing three body parameters in order:
`customer_name`, `repair_number`, `amount_due`. Suggested body: the current pending
payment body, adding “Use the RushX merchant QR above or contact support.” Supply
Meta's required reviewed sample image separately during submission. Do not attach
media to or edit the already-submitted text-only template.

Add this entry to `WHATSAPP_TEMPLATES_JSON` only after approval is independently
confirmed (keep `approval_status:unknown` until then):

```json
"PAYMENT_PENDING_QR": {
  "name": "rushx_payment_pending_qr_v1", "language": "en_US",
  "category": "UTILITY", "approval_status": "unknown", "header_format": "IMAGE",
  "parameters": ["customer_name", "repair_number", "amount_due"]
}
```

The QR variant is selected only when reviewed URL and approved media mapping exist;
otherwise pending-payment events retain the text template. The URL is snapshotted;
changing/removing it blocks old media jobs for review rather than silently changing
payee instructions. This uses Meta's [image-header template component format](https://www.postman.com/meta/whatsapp-business-platform/request/lwtlz1k/send-message-template-interactive).

The new **ninth event**, `PAYMENT_RECEIVED`, uses proposed
`rushx_payment_received_v1`, Utility, en_US, body parameters `customer_name`,
`repair_number`, `verified_amount`, `safe_reference`. Exact proposed copy/examples
are in `templates/whatsapp_utility_catalog.json`. Submit and approve it separately;
add its mapping with `approval_status:approved` only after verification in Meta.
Missing/unknown acknowledgement approval blocks that job, not the original eight
production template mappings. Existing allowlisted Meta test sender, explicit opt-in,
production gate and webhook signature verification remain in force. Do not migrate
or disconnect the WhatsApp Business mobile number. No live send or approval occurs
in automated tests or this PR. Retry eligible configuration-blocked jobs using the
existing admin safe-requeue procedure after setup.

## Migration and rollback

No destructive migration or bulk rewrite. Legacy `payment_summary` with manual
source/currency/verifier/time is normalized by the payment boundary on read; WhatsApp
has no provider-name check. First new balance verification appends an audit record including the prior legacy summary;
legacy balances do not become verified receipts. Existing repair API summary fields
remain `amount_due`, `currency`, `verified_at`. New evidence/audit/receipt fields are
removed from general repair responses and exposed selectively by the payment API.
Legacy zero balances remain usable, but never imply historical receipt of money.

Before rollback stop the WhatsApp worker, disable WhatsApp sends and manual payment
writes, and back up repairs plus `payment_references`. Revert code without dropping
new audit/event/reference fields. Older code still reads the compatible balance
summary; it cannot enforce receipt immutability or understand ninth-event jobs, so
**keep payment writes and new acknowledgement dispatch disabled** until the new
code returns. Do not run old/new payment writers concurrently. Reconcile reservations
and inspect pending jobs before reactivation. Restore audit records from backup only
through a reviewed recovery procedure; never infer historical receipts from statuses.
