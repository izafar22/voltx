# Issue #3 validation — 2026-10-21

Base: latest fetched repair-mvp plus the unmerged PR #2 commit `44c8ef1`.
Implementation branch: `codex/rushx-whatsapp-lifecycle`.

| Check | Actual result |
| --- | --- |
| Backend: `python -m pytest tests -q -rs` | **175 passed, 2 skipped**, 96.92 seconds |
| Frontend: `CI=true npm test -- --watchAll=false --runInBand` | **124 passed**, 10 suites |
| Frontend: `CI=true npm run build` | **Compiled successfully** |
| Pyflakes on service modules and new/updated WhatsApp tests | Passed |
| Python compilation; `git diff --check` | Passed |
| Non-secret env example / eight-template catalog consistency | Passed |

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
