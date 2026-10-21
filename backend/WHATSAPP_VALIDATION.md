# PR #4 validation — lifecycle and manual payments — 2026-10-21

Base: latest fetched repair-mvp plus the unmerged PR #2 commit `44c8ef1`.
Implementation branch: `codex/rushx-whatsapp-lifecycle`.

| Check | Actual result |
| --- | --- |
| Backend: `python -m pytest tests -q -rs` | **222 passed, 2 skipped**, 92.36 seconds |
| Frontend: `CI=true npm test -- --watchAll=false --runInBand` | **131 passed**, 11 suites |
| Frontend: `CI=true npm run build` | **Compiled successfully** |
| Pyflakes on service modules and new/updated WhatsApp tests | Passed |
| Python compilation; `git diff --check` | Passed |
| Non-secret env example / nine-event catalog consistency | Passed |

The full backend suite ran against a locally started test API using a uniquely
named disposable MongoDB database, APP_ENV=test, OTP_MODE=demo,
EXPOSE_DEMO_OTP=true and WHATSAPP_ENABLED=false. The temporary API was stopped
and its database removed afterwards. Auth and Mongo smoke tests create/remove
additional isolated databases. Original application data/configuration was preserved.

The two existing skips were `backend_test.py` cases for an empty owner wallet
and absent withdrawals. Existing FastAPI lifecycle and multipart deprecation
warnings remain; no new test failures remain.

Coverage includes all eight payloads/triggers, no-opt-in and withdrawal, no draft
notifications, published estimate totals/immutability, verified payment balances,
admin-confirmed courier/tracking, stale balance cancellation, concurrent fact edits,
status CAS, alternate lifecycle branches, unsupported statuses/rollbacks, malformed
mapping/unknown approvals, production gates, sender isolation, legacy snapshots,
webhook signatures/body limits/deduplication/sender scope, query-token redaction,
429/5xx/shared throttling, leases, crash-after-acceptance ambiguity, safe replay and
admin-only aggregate metrics. The real-MongoDB test exercises all eight jobs,
indexes, duplicate reconciliation and concurrent worker claims with mocked HTTP.

Every Meta request in automated tests uses `httpx.MockTransport`. No live WhatsApp
message, template submission/change, number registration/migration, production
activation, merge or deployment was performed. These tests do not establish Meta
approval or real delivery; the catalog's approval/submission fields remain unknown.

## Manual payment follow-up

Read both PR payment review comments (6313592124 and 6313705033). Added
PaymentService, PaymentProcessor/ManualPaymentProcessor and PaymentRepository /
MongoPaymentRepository; explicit full manual receipt, unverified customer evidence,
optional reviewed QR and provider-neutral PaymentReceived outbox integration.

47 payment tests cover legacy balance/API compatibility, exact monetary validation,
full-vs-partial/overpayment, admin/customer authorization, private audit projections,
no automatic settlement from references, generated cash IDs, normalized cross-repair
UTR uniqueness, durable idempotency-key conflicts, simultaneous matching/conflicting
writers, interrupted reservation/commit/marker recovery, unchanged repair status,
consent/withdrawal, disabled notifications, alternative injected processor, mocked
acknowledgement payload, pending-notice cancellation and QR approval/configuration.

Seven new React tests cover text fallback, QR display, unverified customer evidence,
explicit admin confirmation and amount matching, stable retry keys, cash references,
paid-state display, lifecycle prerequisite and visible load errors. Existing 124
frontend tests remain green. No frontend dependency was added.

The final targeted payment/WhatsApp pass also extends the disposable real-MongoDB
smoke test with the compound idempotency index, five concurrent identical receipt
requests, duplicate UTR rejection across repairs and one ninth acknowledgement via
MockTransport. See PAYMENTS.md for operator recovery, configuration and rollback.

Intentional limitations: full receipts only, no refunds/reversals, no new zero-balance
repair transition, no automatic resolution of conflicting reservations, and manual
merchant-QR ownership / Meta approval verification. These are documented gates,
not silently inferred facts. The original separate worktree's local environment
edit remains untouched. Nothing was merged, deployed, charged or sent live.
