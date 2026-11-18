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

- [ ] Confirm PR CI passes and review findings are resolved.
- [ ] Obtain explicit merge approval, then verify automatic staging CD and matching frontend/backend commit IDs.
- [ ] Use authorized staging test accounts to verify Google linking, then sign out and sign in through Google to the same dashboard, repairs and addresses.
- [ ] Verify WhatsApp linking/replacement with an authorized allowlisted test number and check the other-session sign-out behavior.
- [ ] Reload and sign in again to confirm saved addresses persist on staging. Submit a test repair with selected addresses and confirm its stored snapshots survive a later address edit.

Real provider interactions and staging acceptance require the merged deployment and user participation. They have not been claimed complete by offline fixtures.

## Compatibility and rollback

No new environment variables, OAuth callback destinations, secondary indexes or existing-data migrations are introduced. `customer_profiles` uses MongoDB `_id` uniqueness. Existing unique phone/Google identity indexes remain required. Saved addresses are bounded to 20 per customer; each update uses a profile revision.

New WhatsApp registrations accept blank email only; verified email is added by connecting Google. Historical email data is preserved, while profile responses expose only Google-verified email. Phone verification timestamps are recorded on normal OTP login as well as authenticated linking.

Repair address fields are additive. Existing address-free requests retain their original idempotency fingerprint. A rollback preserves added MongoDB documents and repair snapshots, although earlier UI versions will not display them. Previously linked Google and phone fields use the existing user identity schema, so normal sign-in can still resolve the same user. Rolling back to code that does not enforce OTP purpose separation could allow an unexpired linking challenge to enter its login path; allow the ten-minute challenge lifetime to expire before an ordinary rollback, or use a separately authorized runbook to invalidate outstanding linking challenges.

## CodeRabbit follow-up (2026-11-19)

All 13 initial review findings were checked against the source and addressed. Phone replacement now commits session retention alongside the phone and epoch in one atomic user update, including when session writes are unavailable. Retention requires an existing, unexpired session and the matching retention epoch, so logout and later account-wide revocation remain effective.

Profile saves capture the auth generation before their requests, cancel old profile reads before publishing data and ignore responses after a session change. Phone verification merges only user fields into the latest profile. Dirty names and open address drafts survive background refresh errors. Address editors pin their initial revision; deletion choices pin their own revision and require refreshed choices to be reviewed before another confirmation. Unknown Google callback statuses are ignored. Repairs navigation stays active across the repair section, and address defaults freeze at the first repair attempt so a late profile response cannot create a duplicate retry.

Regression tests cover these races and strengthen the default-checkbox and phone-verification request assertions. Follow-up validation passed: 187 frontend tests, 65 backend auth/profile tests, the frontend build and 24 profile browser checks. Staging acceptance remains pending.

Rolling back to an earlier auth implementation does not recognize the retained-session exception, so a customer who replaced their phone may need to sign in again. The new phone remains the account identity.
