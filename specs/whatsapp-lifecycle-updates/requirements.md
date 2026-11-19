# WhatsApp lifecycle updates — requirements

Status: FINAL REQUIREMENTS. Finalized with owner authorization on 2026-11-20; source audit prepared 2026-11-19 against `repair-mvp` commit `5206722af8a939d903946f0bdef5dfea51104bf1`.

The owner authorized specification work on 2026-11-19 and requested the final requirements document on 2026-11-20 under the name WhatsApp lifecycle updates. This document records the agreed requirements. Detailed design and implementation tasks require subsequent review before implementation. Finalizing requirements does not authorize merges, template changes, environment changes, live messages or production activation.

## Customer outcome

A customer who explicitly opts in receives WhatsApp messages at meaningful repair milestones, with accurate facts and clear next actions. The RushX account remains the place to review repair progress, estimates and shipment details when a message is delayed or unavailable. Describe this as milestone updates, not continuous or live tracking.

## First-release scope

Reuse and complete the existing messaging implementation. Preserve working WhatsApp OTP, Google sign-in, customer profile, saved addresses, repair authorization and parked functionality. No new messaging platform, marketing messages, automatic incoming-message replies or general chat inbox.

On 2026-11-19 the owner initially selected nine messages and explicit RushX team acceptance before shipping instructions. On 2026-11-20 the owner revised the scope to eight customer messages: combine repair completion and verified balance/payment instructions, retaining WhatsApp estimate-approval confirmation and the separate payment-received acknowledgement. The eight-message scope below supersedes the earlier nine-message scope. The owner clarified and confirmed that team acceptance permits sending the charger for inspection; it does not guarantee repairability or authorize priced repair work. The customer separately approves the published estimate before repair begins.

| Event | Message purpose | Required source facts / customer action |
|---|---|---|
| REQUESTED | Confirm receipt of the enquiry, not technical acceptance | Persisted request number, customer name and charger description; explain that next steps follow review |
| AWAITING_SHIPMENT | Supply inbound shipping instructions after team acceptance | Explicit team acceptance and an approved dispatch address; customer packages/sends only after instructions |
| RECEIVED_AT_VOLTX | Confirm actual receipt at RushX | Operator-recorded physical receipt; no claim that diagnosis is complete |
| ESTIMATE_SENT | Tell the customer an estimate is ready | Persisted valid published estimate in INR; customer reviews and approves/declines in the account |
| CUSTOMER_APPROVED | Acknowledge the customer's approval | Recorded approval of the published estimate; no claim that repair is already complete |
| REPAIR_RESULT (combined completion + balance) | Confirm completed repair and the verified payment position in one update | Recorded completion plus a verified reconciled balance; request payment only for a positive balance, otherwise state that no payment is currently due |
| PAYMENT_RECEIVED | Acknowledge a verified payment | Existing full-receipt verification event and verified amount/safe reference; never infer settlement from uploaded evidence alone |
| SHIPPED_TO_CUSTOMER | Confirm actual return dispatch | Confirmed courier and tracking details; do not imply delivery or live courier tracking |

The normal lifecycle includes exceptions. For version 1, customer-declined, not-repairable, cancelled, diagnosis-in-progress and delivered states remain visible through the existing account/support journey; this release does not add automatic messages for them. Make that limitation explicit in acceptance and customer wording. New exception templates or payment/refund/revised-estimate workflows need a separately reviewed scope change. Do not fabricate payment amounts or alter lifecycle transitions to bypass existing zero-balance limitations.

## Combined completion and balance update

- Send one completion/balance update per repair, only after repair work is recorded complete and the outstanding balance is verified. Recording completion alone does not notify; an unverified/unknown balance is not zero.
- For a positive balance, show the actual INR amount and direct the customer to dashboard/support payment instructions. For a verified zero balance, omit payment instructions and state that no payment is currently due. Do not claim receipt of money unless a receipt is separately verified.
- Support two separately verified template variants for this one customer milestone. A repair gets at most one provider-accepted completion/balance update, not both variants and not the two legacy standalone notices.
- Keep internal REPAIR_COMPLETED and PAYMENT_PENDING business statuses where applicable; this change combines notifications, not lifecycle states. Preserve the existing guards and record the zero-balance onward-shipping limitation for a separate explicit business decision.
- Repeated completion/status/balance saves cannot create additional completion messages. A balance that changes before dispatch makes the old snapshot ineligible; do not send stale payment instructions or silently replace its amount. Subsequent reminders or revised-balance notification flows are outside this release.
- PAYMENT_RECEIVED remains a separate verified-payment acknowledgement. CUSTOMER_APPROVED remains a WhatsApp message. No scheduled reminders or repeat prompts are added.

## Customer consent and destination

- Optional, unchecked, repair-specific consent. Declining does not prevent submitting or managing a repair. Signing in by WhatsApp does not grant lifecycle consent.
- Explain the kinds of updates, show the customer's own current verified number appropriately, and offer Stop WhatsApp updates from repair details.
- Use only the authenticated customer's verified account number. Google-only customers may link and verify a mobile through the existing profile flow, without losing their repair draft. No arbitrary recipient input or administrator redirection.
- Record consent version, source, time, destination and withdrawal. Preserve enough history to audit why a queued message was or was not eligible without placing personal data in logs.
- Withdrawal blocks subsequent queued/retried sends when checked before dispatch; it cannot recall a request already sent to Meta. Keep account access and repair status updates available.
- After phone replacement, do not continue sending to the old destination or automatically transfer repair consent to the new number. Recheck account ownership/verification and consent before dispatch. Version 1 pauses updates for affected repairs; re-enabling requires a later explicit consent flow, not an automatic resend. UI must explain how to follow progress meanwhile. Final race semantics are a design-review item.
- Existing repairs are not silently opted in. Activation does not reconstruct or broadcast old milestones. Historical unsent jobs/outbox items require a reviewed cutoff/quarantine plan; starting a worker must not drain an unreviewed backlog.

## Truthful events and useful messages

- Messages follow committed business events; draft estimates, unsaved shipment details and repeated requests do not notify.
- Request creation and each transition preserve durable event identity and idempotency. Payment acknowledgement uses its own verified receipt event and does not change repair status.
- Never imply technical acceptance, collection, repair success, payment receipt or dispatch before the corresponding verified event.
- The current form advances new repairs straight to AWAITING_SHIPMENT. The owner-approved acceptance-first policy requires removing that automatic action and enforcing the new boundary in the API as well as UI. The exact technical design and implementation remain subject to later review.
- Delayed action prompts must not instruct customers to act on obsolete estimates, shipping instructions, withdrawn consent or paid balances. Define per-event freshness and ordering rules during design; revalidate authoritative facts at dispatch without rewriting historical snapshots.
- No invented greeting, facility address, diagnosis, price, delivery date, warranty or support commitment. Missing required facts prevent the message, while a messaging failure must not erase a successful repair update.
- Use exact, verified Meta template names, language, category, body and positional/header/button parameters. Existing catalog entries are proposals, not evidence of current approval. Confirm all selected templates in the correct account before activation. Do not edit in-review templates or submit replacements without authorization.
- Existing templates refer to the dashboard but do not carry dashboard-link parameters. Preserve that contract unless an approved template variant supports a reviewed HTTPS account link. No authentication tokens, signed-in session links, internal notes, customer addresses or payment-reconciliation secrets in messages.

## Reliable delivery and operations

- Reuse the embedded repair outbox, materialized jobs, separate worker, signed webhook receipts and existing admin metrics/safe replay path.
- Repair handlers must not perform provider network calls. Events and business changes share the durable write; reconciliation must recover from crashes.
- Duplicate events, concurrent workers and repeated/late callbacks must not produce automatic duplicate sends or downgrade delivery state. Do not promise exactly-once provider delivery.
- Keep bounded retries and shared throttling for eligible transient errors; ambiguous acceptance/timeouts go to operator review, not blind replay. Distinguish queued, provider-accepted, delivered, read and failed; acceptance is not proof of delivery.
- Invalid configuration, consent, destination, scope, template or business facts fail closed. A rejected message does not fail or revert a valid repair mutation.
- Use a supervised worker with reviewed MongoDB indexes/permissions, startup readiness, graceful shutdown, health/queue monitoring and a recovery runbook. Never start the worker against live data merely to discover whether it is configured correctly.
- Preserve webhook HMAC checks, bounded input, durable receipt handling and sender/account isolation. Incoming messages do not automatically opt in, invoke repairs or cause replies.
- Operational metrics remain aggregate/admin-only. Secrets and customer personal information must not enter Git, application logs, alert labels or public health endpoints. Retention/deletion and retained deduplication evidence need an explicit design decision.

## Environment separation and rollout

- OTP and lifecycle messaging have separate enablement; disabling lifecycle messages must preserve OTP sign-in and linking. Shared credential changes require a compatibility assessment.
- Current staging explicitly forbids lifecycle messaging. A separately reviewed implementation must provide a narrow, default-off staging test gate, enforced by both API and worker, with dedicated staging data and an explicit authorized-recipient allowlist. Do not relax production isolation or reuse the OTP allowlist implicitly.
- Staging must exercise real approved milestone templates on explicitly authorized test recipients; hello_world can test transport only. Sending test messages requires explicit approval of recipients and test window. No credentials, recipients or customer records in the spec/PR.
- Begin with mocked/offline checks. Verify provider template approval, webhook delivery and supervised worker operation before staged live acceptance. Record actual results; historical tests and OTP delivery are not proof of lifecycle delivery.
- Keep lifecycle messaging disabled until dependencies, selected templates, worker, webhook and consent UI are ready. No broad public website promise until real delivery is verified; the later repair-journey website spec is separate.
- Integrate approved implementation through repair-mvp and staging. Prepare a new production release from the then-verified deployed baseline, promote selected commits through a PR into that new release branch, test/package the merged release SHA, and obtain explicit owner approval before deployment and message activation. Preserve historical release refs. Version agreed before branch creation.
- Activation and rollback must pause API enqueueing and worker dispatch consistently, preserve queued evidence, prevent old/test jobs being sent after re-enabling, and leave OTP and the repair dashboard working. Delivery cannot be recalled; do not bulk-reset or replay jobs.

## Acceptance criteria

1. Selected milestones have verified event-to-template-to-parameter mappings and truthful source facts; the first release includes the eight agreed customer messages, with both combined-message variants verified and enforces the agreed team-acceptance policy.
2. Explicit opt-in/opt-out, verified-number eligibility, withdrawal, phone replacement, account/role isolation and existing-repair behavior pass negative and race tests.
3. New submission cannot send shipping instructions before team acceptance; duplicate/retried submissions create one intended event per actual milestone.
4. Complete authorized staging journey proves committed business events reach the intended recipient, with real provider status receipts and accurate content. Capture redacted evidence for each selected milestone and explain unexercised receipt states.
5. Opted-out, withdrawn, wrong-recipient, stale-action and invalid-fact cases do not send. Failure, retry, crash, receipt ordering and uncertain-delivery cases preserve the existing reliability/security guarantees.
6. Staging remains fail-closed without its dedicated test gate and allowlist, from both API and worker; test jobs cannot be promoted into production.
7. Existing auth/profile/repair/payment tests and applicable frontend/browser/Storybook checks pass. Consent UI works in both themes at 320/375/768/1280, with keyboard and labelled error/loading states.
8. Operator can observe delivery health, stop lifecycle sending without breaking OTP, and recover only demonstrably unsent supported failures. Readiness/cutoff and rollback procedures are reviewed before activation.
9. Production uses the exact approved merged release SHA/artifacts and separately authorized activation, with independently verified revisions and rollback references.

## Approval record

- 2026-11-19: owner agreed to prioritize WhatsApp repair lifecycle updates and authorized preparation of this spec.
- 2026-11-19: owner explicitly approved all nine messages, including payment received, and team acceptance before shipping instructions.
- 2026-11-20: owner requested finalization of requirements.md and specified the name WhatsApp lifecycle updates. Requirements finalized in `specs/whatsapp-lifecycle-updates/requirements.md`.
- 2026-11-20: owner approved the design/UI, requiring preservation of the existing RushX logo, then authorized the eight-message amendment: combined completion/balance, estimate approval retained on WhatsApp, payment receipt separate. Detailed design updated to reflect that amendment; implementation task review remains next.
- Historical status at requirements finalization: implementation tasks were not yet finalized or approved. The subsequent task approval and offline implementation entry below supersede this status; merge and live-operation approvals remain separate.

- 2026-11-20: owner said “lets proceed” after agreeing the eight-message list; authorized updating the spec and preparing the implementation task plan. This does not authorize live sends or production activation.

- 2026-11-20: owner approved proceeding with the implementation task plan. Offline implementation completed on feature/whatsapp-lifecycle-updates; see validation.md. Merge and live operational gates remain separate.
