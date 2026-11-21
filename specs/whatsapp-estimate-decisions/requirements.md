# WhatsApp estimate decisions — requirements

Prepared 2026-11-21. Status: APPROVED. On 2026-11-21 the owner approved the 72-hour validity window, one-tap decisions and separately reviewed static RushX merchant QR with text-only fallback. This feature extends the accepted WhatsApp lifecycle without changing payment verification, repair-team permissions or the website approval path.

## Goal

Let the repair customer approve or decline the currently published estimate from the estimate-ready WhatsApp message. The decision must become the same repair status and estimate decision used by the website, with a durable audit trail and an immediate acknowledgement.

## Customer contract

- The estimate-ready Utility template shows the customer name, repair number and exact INR estimate total before displaying **Approve estimate** and **Decline estimate** quick-reply buttons.
- Recommended decision contract: one clear tap records the decision. There is no free-text `yes`/`no` interpretation.
- Recommended validity window: 72 hours from the estimate-ready message. After expiry, the buttons fail safely and the customer uses the RushX dashboard or support.
- The website remains available and whichever valid channel wins first is authoritative.
- Approve produces the existing approval acknowledgement. Decline produces a concise decline acknowledgement and return-next-step wording; neither promises a refund, payment outcome or dispatch.

## Security and correctness

- Every action is cryptographically unguessable and bound to the repair, customer destination, estimate facts/version, decision, originating message and expiry.
- Only a signed Meta webhook for the configured sender may submit an action. The inbound sender must match the repair's current consented and verified phone.
- The repair must still be `ESTIMATE_SENT`, the persisted estimate must still be `SENT`, and its immutable facts and amount must match the action snapshot.
- An action is single-use and idempotent. Repeated delivery cannot create another history entry or reverse the first decision.
- A stale, expired, malformed, cross-repair, cross-recipient, withdrawn-consent, changed-phone or unknown-message action never changes the repair.
- Concurrent website and WhatsApp decisions use one compare-and-set boundary; exactly one decision wins.
- Audit records include channel, decision, time, estimate fingerprint, source message ID and a non-secret action identifier. Raw tokens, phone numbers and webhook bodies are not logged or exposed to customers.

## Operational boundaries

- The feature is default-off behind a dedicated setting and requires an approved, exact Meta template contract with two quick-reply buttons.
- Existing approved estimate and lifecycle templates remain active while the feature is off.
- Webhook receipt is durable; business processing occurs in the worker, not in the HTTP webhook handler.
- Automated tests use signed synthetic callbacks and mocked Meta transport only.
- Template submission, environment activation, staging sends, merge and production promotion each remain separately authorized operations.

## Payment-due QR message

- When a completed repair has a positive, verified outstanding balance, RushX should send the combined repair-completed/payment-due WhatsApp message with the reviewed RushX merchant QR as an image header.
- The body must show the exact INR amount due, repair number and safe instructions to pay that exact amount. It must state that payment is complete only after RushX verifies receipt.
- The QR must come from the configured RushX merchant asset over reviewed public HTTPS. Customer-supplied URLs, redirects containing credentials, data URLs and per-message arbitrary media are forbidden.
- QR delivery uses a separately approved Utility template contract. Until its exact Meta contract and merchant QR are reviewed, the existing text-only payment-due template remains the safe fallback.
- QR display never marks a payment received, changes the balance, or bypasses the existing administrator receipt verification and idempotency controls.
- QR selection is independently default-off so estimate buttons can be enabled or rolled back without changing payment messaging, and vice versa.

## Acceptance criteria

1. A valid Approve button atomically records `CUSTOMER_APPROVED`, estimate `APPROVED`, approval timestamp and WhatsApp audit data, then queues the existing approval acknowledgement.
2. A valid Decline button atomically records `CUSTOMER_DECLINED`, estimate `DECLINED`, decline timestamp and WhatsApp audit data, then queues a decline acknowledgement.
3. Website decisions record the same audit schema with channel `web` and race safely with WhatsApp.
4. Duplicate callbacks return the previously recorded result without a second mutation or acknowledgement.
5. All negative security cases fail closed and remain observable through aggregate action outcomes without PII.
6. Existing eight-message positive lifecycle, OTP, payment, webhook receipt and staging-isolation tests remain green when the feature is off.
7. With the reviewed QR feature enabled, the positive-balance combined message uses the exact approved image-header template and reviewed QR URL; zero-balance and payment-received messages never include the QR.
8. Missing/unreviewed/invalid QR configuration cannot produce arbitrary media or block the underlying repair/payment business mutation; it uses the approved text-only contract and records aggregate readiness state.

## Approval record

- **Approved:** 72-hour action validity window.
- **Approved:** one-tap Approve/Decline after the message displays the exact repair number and amount.
- **Approved:** separately reviewed static RushX merchant QR in the positive-balance message, with text-only fallback until the image-header Utility template and QR asset are approved.
