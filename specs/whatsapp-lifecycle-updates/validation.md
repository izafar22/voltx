# WhatsApp lifecycle updates — validation

Verified locally 2026-11-20 on `feature/whatsapp-lifecycle-updates`. This is offline implementation evidence, not live provider approval, delivery or deployment evidence.

## Executed checks

| Check | Command / scope | Result |
|---|---|---|
| Backend regression | Disposable loopback MongoDB/API; backend virtualenv `python -m pytest` | 429 passed, 3 skipped; 1144 warnings (primarily existing deprecations) |
| Final activation/control regressions | `python -m pytest tests/test_lifecycle_v3.py -q --tb=short` | 29 passed after final instruction-manifest/control changes; includes one additional concurrency test added after the full-suite run |
| Focused auth/profile/transport/staging regression | pytest selected lifecycle/auth/profile/WhatsApp/staging modules | 174 passed before final control-only changes |
| Frontend unit | `CI=true npm test -- --watchAll=false --runInBand` | 191 passed, 19 suites, including final phone-dialog submit propagation fix |
| Frontend production bundle | `npm run build` | Passed after final UI changes |
| App browser regression | `./node_modules/.bin/playwright test` in frontend/e2e | 140 passed at 320/375/768/1280, both themes |
| Final lifecycle browser check | `./node_modules/.bin/playwright test lifecycle.spec.cjs` | 24 passed after final pinned admin preview and phone-dialog changes |
| Storybook build/browser | Repository Storybook build and browser test runner | 163 checks passed; uses production consent component |
| Diff hygiene | `git diff --check` | Passed |

All provider transport was mocked. The integrated API test exercises the eight positive-balance milestone messages; verified-zero completion is tested separately. Coverage includes consent withdrawal before intent, session/generation binding, stale balance/instructions, outbox ordering with two workers on standalone MongoDB, atomic combined-result reservation, duplicate requests, initial activation races, default-off environment isolation and read-only readiness. Existing OTP and session-retention regressions remain green.

## Review findings addressed

Source differed from the original audit: the existing form automatically advanced shipping and hardcoded opt-out; API permitted customer acceptance; worker did not share staging isolation. The implementation now uses explicit admin acceptance and bound consent. Browser testing caught checkbox mobile overflow; selectors now exclude checkboxes from full-width input styling. Phone-verification portal submits now stop propagation to preserve an already-completed repair draft without accidentally submitting it. Admin acceptance pins the preview being acknowledged and refreshes on conflict. Combined-event construction uses the committed estimate post-image for freshness digests.

## Remaining gates and limitations

Code review and final-head CI must pass before merge approval. No live Meta inventory/approval has been verified, and proposed combined templates must be audited before activation. No service installed, live configuration changed, indexes created, migrations run, or customer messages sent. Authorized staging requires separately approved sender/recipient/window, configuration, indexes and worker readiness; then actual template/receipt evidence and rollback rehearsal.

Zero-balance completion is supported as a notification, but the pre-existing zero-balance onward-return transition is deferred. Withdrawal or phone changes cannot recall an attempt already authorized and in flight to Meta. No existing-repair re-consent, automatic backlog reconstruction, reminders or retention cleanup is introduced. Production promotion must use a new release branch, merged promotion PR and tested/approved final-SHA artifacts.

## PR #74 review follow-up (2026-11-20)

Initial final-head CI passed: 431 backend tests (2 skipped), 191 frontend tests, 140 app browser checks and 163 Storybook checks, plus builds. Review identified 13 valid issues. Corrections include consistent safe response derivation, retired activation history, transient activation-read deferral with pre-HTTP intent clearing, sparse index options, payment notification failure containment, charger-description validation/enrichment, zero-parameter test-template serialization, stop-before-claim, direct-loopback-only test databases, keyed repair view state, 401 retry integrity and historical approval wording.

Revised local checks: focused lifecycle/payment/WhatsApp suite 175 passed; frontend 192 passed; production build passed; lifecycle browser suite 32 passed including route-change confirmation reset at all four widths and both themes. Revised-head CI is tracked in the PR; no merge, activation or live operation was performed.

## CI regression and follow-up (2026-11-20)

CI at 9d5ec9f failed one existing safety test because newly tightened description validation rejected a registered charger without a name. The fix preserves the existing registered-charger reporting contract and supplies a neutral notification description; the existing safety test is unchanged. Full local backend regression then passed 448 tests (3 skipped) before the subsequent recovery/scope additions.

Follow-up review corrections bind consent to the originating sender scope and persist bounded payment-notification construction intents. Focused lifecycle/payment/safety/WhatsApp regressions passed 209 tests, including standalone MongoDB concurrent recovery, fixed deadlines, duplicate payment retries, expiry/withdrawal, retired sender consent and registered-charger fallback. Final local full backend suite passed 455 tests (3 skipped, 1181 warnings) with a fresh disposable API/MongoDB, after all recovery/scope additions. Final-head CI evidence is tracked in the PR. No live operations occurred.

Final CI on 41fbe6c passed both branch and PR runs: 455 backend tests (3 skipped), 192 frontend tests, 148 app browser checks and 163 Storybook checks. Subsequent review identified recovery scan starvation behind 200 deferred repairs. The worker now traverses bounded batches by MongoDB _id with an in-memory rotating cursor and wraps to revisit deferred work; targeted ordering reconciliation does not alter that cursor. Mock and standalone-Mongo regression tests cover advancement and wraparound; the focused lifecycle/payment/safety/WhatsApp suite passed 211 tests after this change. Follow-up CI is tracked in the PR.

## Live Meta contract compatibility follow-up (2026-11-20)

Read-only API audit found approved locale en and a two-parameter REQUESTED body, unlike the proposed en_US/three-parameter source. The active catalog/serializer now use those exact contracts; the legacy path is preserved. Staging validation uses its independent selected-sender binding without requiring an unrelated Meta test sender. New staging webhook isolation accepts known dispatched stage receipts even while paused and ignores unrelated OTP/production/unknown-recipient data.

Local full backend suite passed 460 tests (3 skipped) after the locale/parameter changes. After the additional staging webhook guard, the focused lifecycle/payment/safety/WhatsApp/staging suite passed 240 tests. After adding the independent provider-contract snapshot regression, the focused suite passed 241 tests. Final-head CI is tracked in the follow-up PR. No frontend implementation changed. Operator setup, explicit approvals, template submission state and remaining live acceptance gates are in staging-acceptance.md. No message delivery is claimed.

## Authorized staging acceptance and payment-gate follow-up (2026-11-21)

An owner-authorized, allowlisted staging journey reached all eight positive-balance milestones. Aggregate provider receipts recorded all eight jobs as delivered on their first attempt; no production message or production configuration was used. The activation was then paused, the worker stopped and all three staging messaging gates restored to false.

The journey exposed a source/runtime mismatch: the blanket staging middleware rejected the repair balance and receipt endpoints even during the active lifecycle test window. The temporary acceptance run used the same payment service layer to finish those two synthetic staging records. The follow-up hotfix narrows the middleware exception to repair-payment paths whose repair consent matches the configured activation and allowlisted destination, while the activation is live and the worker heartbeat is current. Paused, expired, disabled, unrelated-repair, wallet, top-up and production paths remain blocked. A fresh UI-only acceptance run remains required after merge and automatic staging deployment.
