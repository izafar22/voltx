# WhatsApp estimate decisions — design

Status: APPROVED on 2026-11-21.

## Message contract

Add a new proposed Utility template key `ESTIMATE_SENT_ACTIONABLE`, leaving `ESTIMATE_SENT` unchanged. It uses the same three body parameters and two quick-reply buttons in this exact order:

1. `Approve estimate`
2. `Decline estimate`

Activation requires the live Meta inventory to match the reviewed name, locale, category, body parameters and buttons exactly. The feature gate selects the actionable variant only for newly published estimates; old messages and jobs are never rewritten.

## Action token

The worker creates a compact authenticated payload for each button from a dedicated action secret. Claims bind version, repair ID, decision, estimate fingerprint, consent destination fingerprint and expiry. Only a digest/action ID is retained for audit; secrets and raw payloads are never persisted in repair history or logs.

The inbound callback must also reference the originating outbound WhatsApp message ID. Verification compares the signed claims with the dispatched job, current repair, current customer phone generation and consent scope.

## Durable processing

The signed webhook validates size, sender metadata and signature, extracts only supported quick-reply callbacks, and inserts a deduplicated `whatsapp_action_inbox` record. It performs no repair mutation and sends no network response message.

The existing supervised worker claims inbox records with a lease. It revalidates activation, expiry, job/message correlation, current identity/consent, estimate fingerprint and status. It then performs one repair-document compare-and-set update that writes the status, estimate decision, decision audit and status history, increments revision, and appends the eligible acknowledgement event/outbox record.

Terminal aggregate outcomes are `applied`, `duplicate`, `expired`, `stale`, `identity_changed`, `consent_withdrawn`, `invalid`, and `failed`. Unknown or unsupported inbound messages are ignored without storing their text.

## Race and replay behavior

- Website and WhatsApp both require current `ESTIMATE_SENT` plus current revision/estimate fingerprint.
- The first successful decision wins. A later identical WhatsApp callback is `duplicate`; a conflicting decision is `stale`.
- A callback accepted by HTTP but processed after expiry, pause, phone/consent change or estimate/status change is rejected at the worker boundary.
- A crash before the repair CAS leaves the inbox retryable. A crash after CAS observes the stored action ID and becomes duplicate without a second acknowledgement.

## Acknowledgements

Approve reuses the existing `CUSTOMER_APPROVED` lifecycle template. Decline uses a separately reviewed Utility acknowledgement contract; it is an alternate-branch acknowledgement and does not alter the eight-message positive path. No free-form customer text is interpreted.

## Positive-balance QR variant

Add a proposed `REPAIR_RESULT_DUE_QR` contract with the same positive-balance body parameters as `REPAIR_RESULT_DUE` and an IMAGE header. Selection requires both an independent feature gate and the existing reviewed-QR configuration. The worker validates that the media URL exactly equals the configured reviewed HTTPS asset before serializing the template payload.

The QR is a presentation aid only. The authoritative balance remains the verified payment summary, and `PAYMENT_RECEIVED` remains exclusively driven by a verified receipt. `REPAIR_RESULT_CLEAR`, approval acknowledgements and shipment messages cannot select the QR variant.

Readiness audits the exact template name, locale, category, parameter order, IMAGE header and QR review flag. Invalid or absent optional QR configuration selects the unchanged approved text-only positive-balance template; it never substitutes an unapproved media message.

## Rollout

1. Merge code with the feature disabled.
2. Audit/submit and obtain approval for the actionable estimate, decline acknowledgement and positive-balance QR templates.
3. Configure a dedicated action secret, reviewed merchant QR asset and exact template manifest in staging.
4. Run signed-callback negative tests and an owner-authorized recipient/window acceptance.
5. Pause/disable after testing; production requires separate release and activation approval.

Rollback disables actionable selection and inbound action processing first. Existing website approval and the non-actionable estimate template continue unchanged; durable action evidence is retained.
