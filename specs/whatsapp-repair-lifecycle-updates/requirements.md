# WhatsApp repair lifecycle updates — requirements

Status: DRAFT FOR OWNER REVIEW. Prepared 2026-11-19 against `repair-mvp` commit `5206722af8a939d903946f0bdef5dfea51104bf1`.

The owner authorized specification work on 2026-11-19, following the customer-profile release. Requirements, design and implementation tasks have not yet been approved. This spec does not authorize implementation, merges, template changes, environment changes, live messages or production activation.

## Customer outcome

A customer who explicitly opts in receives WhatsApp messages at meaningful repair milestones, with accurate facts and clear next actions. The RushX account remains the place to review repair progress, estimates and shipment details when a message is delayed or unavailable. Describe this as milestone updates, not continuous or live tracking.

## Proposed first-release scope

Reuse and complete the existing messaging implementation. Preserve working WhatsApp OTP, Google sign-in, customer profile, saved addresses, repair authorization and parked functionality. No new messaging platform, marketing messages, automatic incoming-message replies or general chat inbox.

Two scope choices await the owner: whether to include the existing payment-received acknowledgement alongside the eight repair messages, and whether shipping instructions require explicit team acceptance. The recommended draft below includes both. See Decisions in design.md; do not infer approval from this draft.

| Event | Message purpose | Required source facts / customer action |
|---|---|---|
| REQUESTED | Confirm receipt of the enquiry, not technical acceptance | Persisted request number, customer name and charger description; explain that next steps follow review |
| AWAITING_SHIPMENT | Supply inbound shipping instructions after acceptance (proposed) | Explicit team acceptance and an approved dispatch address; customer packages/sends only after instructions |
| RECEIVED_AT_VOLTX | Confirm actual receipt at RushX | Operator-recorded physical receipt; no claim that diagnosis is complete |
| ESTIMATE_SENT | Tell the customer an estimate is ready | Persisted valid published estimate in INR; customer reviews and approves/declines in the account |
| CUSTOMER_APPROVED | Acknowledge the customer's approval | Recorded approval of the published estimate; no claim that repair is already complete |
| REPAIR_COMPLETED | Confirm recorded completion of repair work | Actual completion; distinguish remaining payment and return steps |
| PAYMENT_PENDING | Explain the verified outstanding balance | Positive reconciled amount due; direct customer to account/support for instructions |
| PAYMENT_RECEIVED | Acknowledge a verified payment (scope decision pending) | Existing full-receipt verification event and verified amount/safe reference; never infer settlement from uploaded evidence alone |
| SHIPPED_TO_CUSTOMER | Confirm actual return dispatch | Confirmed courier and tracking details; do not imply delivery or live courier tracking |

The normal lifecycle includes exceptions. For version 1, customer-declined, not-repairable, cancelled, diagnosis-in-progress and delivered states remain visible through the existing account/support journey; this draft does not add automatic messages for them. Make that limitation explicit in acceptance and customer wording. New exception templates or payment/refund/revised-estimate workflows need a separately reviewed scope change. Do not fabricate payment amounts or alter lifecycle transitions to bypass existing zero-balance limitations.

## Customer consent and destination

- Optional, unchecked, repair-specific consent. Declining does not prevent submitting or managing a repair. Signing in by WhatsApp does not grant lifecycle consent.
- Explain the kinds of updates, show the customer's own current verified number appropriately, and offer Stop WhatsApp updates from repair details.
- Use only the authenticated customer's verified account number. Google-only customers may link and verify a mobile through the existing profile flow, without losing their repair draft. No arbitrary recipient input or administrator redirection.
- Record consent version, source, time, destination and withdrawal. Preserve enough history to audit why a queued message was or was not eligible without placing personal data in logs.
- Withdrawal blocks subsequent queued/retried sends when checked before dispatch; it cannot recall a request already sent to Meta. Keep account access and repair status updates available.
- After phone replacement, do not continue sending to the old destination or automatically transfer repair consent to the new number. Recheck account ownership/verification and consent before dispatch. Proposed version 1 pauses updates for affected repairs; re-enabling requires a later explicit consent flow, not an automatic resend. UI must explain how to follow progress meanwhile. Final race semantics are a design-review item.
- Existing repairs are not silently opted in. Activation does not reconstruct or broadcast old milestones. Historical unsent jobs/outbox items require a reviewed cutoff/quarantine plan; starting a worker must not drain an unreviewed backlog.

## Truthful events and useful messages

- Messages follow committed business events; draft estimates, unsaved shipment details and repeated requests do not notify.
- Request creation and each transition preserve durable event identity and idempotency. Payment acknowledgement uses its own verified receipt event and does not change repair status.
- Never imply technical acceptance, collection, repair success, payment receipt or dispatch before the corresponding verified event.
- The current form advances new repairs straight to AWAITING_SHIPMENT. The proposed acceptance-first policy must remove that automatic action and enforce the new boundary in the API as well as UI. This is an explicit proposed business change requiring approval.
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

1. Selected milestones have verified event-to-template-to-parameter mappings and truthful source facts; owner confirms first-release scope and team-acceptance policy.
2. Explicit opt-in/opt-out, verified-number eligibility, withdrawal, phone replacement, account/role isolation and existing-repair behavior pass negative and race tests.
3. New submission cannot send shipping instructions before team acceptance if the proposed policy is approved; duplicate/retried submissions create one intended event per actual milestone.
4. Complete authorized staging journey proves committed business events reach the intended recipient, with real provider status receipts and accurate content. Capture redacted evidence for each selected milestone and explain unexercised receipt states.
5. Opted-out, withdrawn, wrong-recipient, stale-action and invalid-fact cases do not send. Failure, retry, crash, receipt ordering and uncertain-delivery cases preserve the existing reliability/security guarantees.
6. Staging remains fail-closed without its dedicated test gate and allowlist, from both API and worker; test jobs cannot be promoted into production.
7. Existing auth/profile/repair/payment tests and applicable frontend/browser/Storybook checks pass. Consent UI works in both themes at 320/375/768/1280, with keyboard and labelled error/loading states.
8. Operator can observe delivery health, stop lifecycle sending without breaking OTP, and recover only demonstrably unsent supported failures. Readiness/cutoff and rollback procedures are reviewed before activation.
9. Production uses the exact approved merged release SHA/artifacts and separately authorized activation, with independently verified revisions and rollback references.

## Approval record

- 2026-11-19: owner agreed to prioritize WhatsApp repair lifecycle updates and authorized preparation of this spec.
- Requirements: pending owner review, including the two scope decisions above.
- Design: audit only; not approved.
- Implementation tasks: not finalized or approved; no implementation authorized by this draft.
