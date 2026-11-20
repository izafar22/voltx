# WhatsApp lifecycle staging acceptance

Status: IN_PROGRESS. Operator verification date: 2026-11-20. No lifecycle test messages have been sent and no test window has started.

## Scope and authorization

The owner requested end-to-end completion and explicitly approved staging-only worker/index setup and a 60-minute test window, starting only after template approval and readiness pass. The sole approved recipient is recorded privately in staging configuration (ending 7681); no full recipient number or credentials belong in this document. Production deployment/activation and messages to other recipients are outside this authorization.

## Verified integration and runtime

PR #74 merged to repair-mvp at b97872339db3bb41316e926e2aac2ffb8e085a94. Automatic staging run [44680537336](https://github.com/izafar22/voltx/actions/runs/44680537336) passed on attempt 2 and deployed frontend/backend release 492. Restricted SSH independently confirmed matching source revisions and an active backend. The first attempt exposed the unchanged pre-existing rate-limit bucket initialization race; thresholds and tests were not weakened.

Read-only audit on 2026-11-20 confirmed the approved receiving address is now valid, staging isolation passes, and existing WhatsApp OTP configuration is retained. Lifecycle sending was disabled, with no activation control, no lifecycle queue jobs, no embedded outbox work and no pending construction intents at audit time. No historical backlog was rewritten.

## Authorized staging preparation

- Installed the five missing index definitions from services.lifecycle_readiness.INDEX_PLAN, including the existing sparse outbox contract; inspected all definitions first and dropped/replaced no index. Verified none remain missing.
- Installed rushx-staging-whatsapp.service for the same release and non-root rushx-staging account as the API. It uses the same backend and staging override environment files, read-only readiness preflight, SIGTERM drain and the reviewed hardening/shutdown controls. It remains stopped and disabled pending readiness.
- Prepared staging-only mode, the single authorized recipient, matching selected sender and a fresh activation UUID in the protected backend environment file. All three send gates remain false. Generated a missing webhook verification token privately. Preserved file ownership/mode and a root-only private backup. No credential values are recorded here.
- Did not restart the API or start/enable the worker during preparation. The API still uses its prior loaded environment until the final reviewed configuration is complete.

## Remaining readiness gates

The running API initially lacked META_APP_SECRET, WHATSAPP_VERIFY_TOKEN, WHATSAPP_TEST_PHONE_NUMBER_ID and the lifecycle template manifest. The verification token is prepared in the protected file; the genuine app secret and lifecycle manifest require account audit. The compatibility patch removes the unrelated test-number prerequisite from dedicated staging mode. The WABA ID was not present in staging configuration. The selected sender is already used by staging OTP; review sender/app webhook sharing before any change that could affect existing delivery. Preserve OTP credentials and production callback behavior.

Owner completed Meta sign-in/two-factor approval. Read-only UI/API audits verified the selected sender belongs to the intended account. Eight existing Utility templates and the separate OTP template are approved in locale en; the request acknowledgement has two body parameters. No app is subscribed to the account webhook. Five existing Utility templates can be reused; a clearer inspection-accepted template, both combined-result variants and payment receipt were explicitly approved by the owner for submission and are PENDING Meta review. Existing approved templates and OTP were not edited. See live-template-audit.json and meta-template-submission.json.

| Logical variant | Proposed template | Locale | Live approval / full components |
|---|---|---|---|
| REQUESTED | rushx_repair_requested | en | APPROVED (audited) |
| AWAITING_SHIPMENT | rushx_awaiting_shipment_v1 | en | PENDING (submitted) |
| RECEIVED_AT_VOLTX | rushx_charger_received | en | APPROVED (audited) |
| ESTIMATE_SENT | rushx_estimate_ready | en | APPROVED (audited) |
| CUSTOMER_APPROVED | rushx_estimate_approved | en | APPROVED (audited) |
| SHIPPED_TO_CUSTOMER | rushx_return_shipped | en | APPROVED (audited) |
| PAYMENT_RECEIVED | rushx_payment_received_v1 | en | PENDING (submitted) |
| REPAIR_RESULT_DUE | rushx_repair_completed_balance_v1 | en | PENDING (submitted) |
| REPAIR_RESULT_CLEAR | rushx_repair_completed_no_balance_v1 | en | PENDING (submitted) |

## Acceptance sequence after readiness

1. Audit exact live templates, body/ordered parameters, static/dynamic components, locale, Utility category and approval. Review missing variants with the owner before submitting or editing templates.
2. Verify authentic app/test-sender metadata, signed webhook routing and staging-only callback compatibility. Complete protected configuration without exposing secrets or rotating working OTP credentials.
3. Run read-only readiness, review aggregate backlog and install no additional indexes without checking their contract. Activate the fresh scope for the approved 60-minute window, then start the worker and verify heartbeat before enabling a customer opt-in journey.
4. Use fresh, clearly synthetic staging repairs and the sole approved recipient. Exercise REQUESTED, explicit team acceptance/instructions, received, estimate ready, customer approval, combined completion/verified positive balance, verified payment receipt and confirmed return tracking. Observe dispatch/receipt before advancing where freshness requires it. No actual funds transfer or physical shipment is implied by synthetic fixtures.
5. Test the alternate verified-zero completion separately; do not invent a payment receipt or unsupported zero-balance onward-return transition. Check opt-out/withdrawal, duplicates, phone change and pause/recovery boundaries under the same authorized scope.
6. Record redacted sent/delivered receipt evidence and recipient confirmation without claiming read receipts unless observed. Pause the activation and stop the worker at the end. Record remaining gaps and production promotion as a separate approval step.

## Evidence still pending

Live template audit, webhook subscription verification, active worker heartbeat, actual eight-message journey, alternate zero-balance message, provider receipt evidence and rollback/pause rehearsal are NOT COMPLETE.

A compatibility patch is under verification: active v3 templates use the audited en locale and the two-parameter request acknowledgement. Legacy contracts remain unchanged. Staging uses its explicit isolated sender binding and does not require an unrelated Meta test-number ID; test/production still require that independent identifier. The installed worker must be repinned to the same merged API release after this patch is separately approved and deployed, before activation.

App-level audit: the RushX API app is unpublished, its existing default callback points to the earlier Render backend, and the messages field is subscribed at app level. The selected WABA has no subscribed app. Meta displays a warning that unpublished apps receive dashboard test webhooks only, so real delivery receipts require publication readiness review. The default callback was not changed. Staging receipt ingestion is hardened to persist only receipts correlated to dispatched/accepted staging jobs for the selected sender; unrelated OTP/other-environment receipts are acknowledged without storage. The genuine app secret must be entered privately by the operator. No app publication, callback override or new app subscription has been performed.
