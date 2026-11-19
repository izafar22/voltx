# Customer profile validation

Implementation authorized 2026-11-18 on `feature/customer-profile`, based on `repair-mvp` commit `96de7ed`. This records local implementation evidence, not staging or production deployment.

## Executed checks

| Check | Result |
|---|---|
| Full backend suite, `cd backend && python -m pytest` | 398 passed, 3 skipped. Existing deprecation warnings remain. |
| Profile-focused backend suite after adding write rate limits | 14 passed. Includes real MongoDB concurrent address writes and Google identity ownership races. |
| Frontend tests, `cd frontend && CI=true npm test -- --watchAll=false --runInBand` | 18 suites, 173 tests passed. |
| Frontend build, `cd frontend && npm run build` | Passed. |
| App browser checks, `cd frontend/e2e && npx playwright test --config playwright.config.cjs` | 116 passed, including 24 new profile checks across Google-only, WhatsApp-only and dual-method states, both themes and 320/375/768/1280 widths. |
| Storybook build, `cd frontend && npm run build-storybook` | Passed. Includes production sign-in-method components for all three account states. |
| Storybook browser/accessibility/visual checks, `cd frontend/e2e && npx playwright test --config storybook.playwright.config.cjs` | 151 passed. |
| `git diff --check` | Passed. |

Backend tests used a loopback-only MongoDB instance and disposable databases. The local disposable API ran on port 8015 with `APP_ENV=test`, demo OTP and a test-only signing secret. Provider calls were mocked. Frontend browser tests use deterministic API fixtures; they validate interactions and rendering, while backend tests establish persistence and authentication behavior.

The full suite passed after correcting an unnecessary address lookup on address-free repair submissions and preserving the repair endpoint's existing ignored-field compatibility. Only client-supplied authoritative address snapshots are explicitly rejected. The final profile-write rate limit and same-account Google/WhatsApp sign-in journey received an additional focused regression run.

## Important coverage

- Customer authorization, origin rejection, protected identity fields and full-name persistence.
- MongoDB address creation races, revision conflicts, default integrity, explicit default deletion and cross-customer isolation.
- Google linking success, conflicting identity ownership, unverified email, changed initiating session, cancellation and replay.
- WhatsApp proof separation from normal login, cross-session rejection, incorrect/expired OTP, provider failure and ownership conflicts.
- Verified phone replacement preserves the initiating session and invalidates other sessions. The replacement phone signs in to the original customer ID.
- Server-owned repair snapshots remain unchanged after saved-address deletion and idempotent retries. Charger-owner redaction excludes customer addresses.
- Profile reload, name/address persistence, mobile verification UI, full repair-form navigation, inline address-dialog draft preservation, accessibility and responsive layout.

## Staging acceptance after merge approval

- [x] Confirm PR CI passes and review findings are resolved. PR #69 passed CI and CodeRabbit; all 13 initial review threads were resolved.
- [x] Obtain explicit merge approval, then verify automatic staging CD and matching frontend/backend commit IDs. Owner-approved merge deployed commit `5206722af8a939d903946f0bdef5dfea51104bf1`, CI run `44388398859`; both release paths match and the backend is active.
- [x] Use authorized staging test accounts to verify Google linking, then sign out and sign in through Google to the same dashboard, repairs and addresses.
- [x] Verify WhatsApp linking/replacement with an authorized allowlisted test number and check the other-session sign-out behavior.
- [x] Reload and sign in again to confirm saved addresses persist on staging. Submit a test repair with selected addresses and confirm its stored snapshots survive a later address edit.

Staging acceptance is complete based on the live evidence below and owner confirmation on 2026-11-19 that the remaining mobile replacement/session revocation and fresh Google sign-in checks work. These manual results are distinct from offline fixture coverage.

## Compatibility and rollback

No new environment variables, OAuth callback destinations, secondary indexes or existing-data migrations are introduced. `customer_profiles` uses MongoDB `_id` uniqueness. Existing unique phone/Google identity indexes remain required. Saved addresses are bounded to 20 per customer; each update uses a profile revision.

New WhatsApp registrations accept blank email only; verified email is added by connecting Google. Historical email data is preserved, while profile responses expose only Google-verified email. Phone verification timestamps are recorded on normal OTP login as well as authenticated linking.

Repair address fields are additive. Existing address-free requests retain their original idempotency fingerprint. A rollback preserves added MongoDB documents and repair snapshots, although earlier UI versions will not display them. Previously linked Google and phone fields use the existing user identity schema, so normal sign-in can still resolve the same user. Rolling back to code that does not enforce OTP purpose separation could allow an unexpired linking challenge to enter its login path; allow the ten-minute challenge lifetime to expire before an ordinary rollback, or use a separately authorized runbook to invalidate outstanding linking challenges.

## CodeRabbit follow-up (2026-11-19)

All 13 initial review findings were checked against the source and addressed. Phone replacement now commits session retention alongside the phone and epoch in one atomic user update, including when session writes are unavailable. Retention requires an existing, unexpired session and the matching retention epoch, so logout and later account-wide revocation remain effective.

Profile saves capture the auth generation before their requests, cancel old profile reads before publishing data and ignore responses after a session change. Phone verification merges only user fields into the latest profile. Dirty names and open address drafts survive background refresh errors. Address editors pin their initial revision; deletion choices pin their own revision and require refreshed choices to be reviewed before another confirmation. Unknown Google callback statuses are ignored. Repairs navigation stays active across the repair section, and address defaults freeze at the first repair attempt so a late profile response cannot create a duplicate retry.

Regression tests cover these races and strengthen the default-checkbox and phone-verification request assertions. Follow-up validation passed: 187 frontend tests, 65 backend auth/profile tests, the frontend build and 24 profile browser checks. Staging acceptance was subsequently completed; see the live acceptance record below.

Rolling back to an earlier auth implementation does not recognize the retained-session exception, so a customer who replaced their phone may need to sign in again. The new phone remains the account identity.

## Live staging acceptance — 2026-11-19 (complete)

Verified the deployed application through its real browser UI, with authorized test accounts and synthetic staging data. No production records were changed.

| Check | Evidence / result |
|---|---|
| Deployment | Frontend and backend at `5206722af8a939d903946f0bdef5dfea51104bf1`; staging CD run `44388398859` succeeded. |
| Existing profile | Verified Google and WhatsApp methods, saved name and existing address visible after a full reload. |
| Saved-address persistence | Created a clearly labelled synthetic address through Profile and confirmed it survived reload. |
| Repair creation | Created synthetic repair `REP-10002` through the full form, selecting the synthetic address for both pickup and delivery. |
| Address snapshots | Edited the saved synthetic address, then reopened the repair: both snapshots retained the original details. After approved address deletion, the snapshots still remained. |
| Cleanup | Owner approved cancellation of `REP-10002` and deletion of only the synthetic saved address. Cancellation is confirmed, and the original customer address/default is preserved. |
| Real WhatsApp sign-in | The allowlisted customer completed real provider OTP sign-in in an independent browser, reaching the same dashboard and repair history including the test repair. No OTP or session token is recorded here. |
| Mobile replacement / other-session sign-out | Owner confirmed on 2026-11-19 that the remaining mobile replacement and other-session sign-out checks were tested and work. This is owner-reported acceptance; the agent did not repeat the test. |
| Fresh Google sign-in | Owner confirmed on 2026-11-19 that the remaining fresh Google sign-in check was tested and works. This is owner-reported acceptance; the agent did not repeat the test. |

The staging provider was activated with approved credentials and the exact approved production authentication template. The allowlist contains two owner-controlled test recipients. Credentials and recipients remain in the VM's protected environment file, outside Git. Staging lifecycle WhatsApp notifications remain disabled. Real number changes are completed by the owner under the browser credential-change policy.

## Production deployment — 2026-11-19

Owner requested production promotion, approved the production baseline/release-branch preparation and PR, and supplied operator access for cutover. Release `release_20261119_version1.1.0` retains the tested commit `479d2ee1e7337bd3db46a898d7a6ffb53887a994` for both components. It selectively applies this feature to frontend 1.0.7, whose backend tree matches running backend 1.0.3.

Exact candidate CI run 44462064627 passed 377 backend tests (2 skipped), 187 frontend tests, 116 app browser checks and 151 Storybook checks, plus frontend/Storybook builds and deployment rollback regressions. Release-branch CI run 44464527144 also passed. The lower backend count versus full staging reflects exclusion of unrelated staging-only changes.

Production preflight verified the unchanged dependency requirement file, a fresh virtual environment pinned to the existing runtime versions, application import, production/provider mode, profile route, existing index contracts and normalized phone identity invariants. The database audit was read-only; no new migration was run.

After cutover, the independent restricted SSH lookup resolved both release directories to the exact SHA and reported a nonzero backend PID. Public HTTPS checks passed for homepage, profile SPA route, both API hosts, profile API rejection without authentication, and new profile OpenAPI registration. Served manifest and main JS/CSS matched the staged tested artifact byte for byte. No production OTP messages or authenticated customer-data test writes were performed; real provider/profile acceptance evidence remains the staging and owner-completed checks above.

Protected server backup and paired rollback script: `/var/backups/rushx/customer-profile-20261119T055839Z`. Existing frontend 1e5da338 and backend 144e1236 remain intact. Rollback was prepared, not rehearsed on production. See `docs/CUSTOMER_PROFILE_PRODUCTION_RELEASE.md` for the ten-minute linking-challenge caveat.
