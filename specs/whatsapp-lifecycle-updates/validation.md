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
