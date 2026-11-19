# Customer profile implementation tasks

Prepared 2026-11-18 from the approved [requirements](requirements.md) and [design](design.md). Task plan approved and implementation authorized by the owner on 2026-11-18. Implementation is on `feature/customer-profile`; PR review and staging acceptance are tracked below.

Integration target: `repair-mvp`, followed by its existing staging CI/CD. Each task includes its regression tests. Merge approval remains separate from task approval.

## Sequence and dependencies

| Task | Deliverable | Depends on | Status |
|---|---|---|---|
| CP-01 | Profile contracts and MongoDB persistence | — | DONE |
| CP-02 | Saved-address APIs and defaults | CP-01 | DONE |
| CP-03 | Google identity linking | CP-01 | DONE |
| CP-04 | WhatsApp mobile linking and replacement | CP-01 | DONE |
| CP-05 | Profile page, dashboard summary and navigation | CP-01 | DONE |
| CP-06 | Google and WhatsApp verification interfaces | CP-03, CP-04, CP-05 | DONE |
| CP-07 | Saved-address management interface | CP-02, CP-05 | DONE |
| CP-08 | Repair address snapshots and form integration | CP-02, CP-07 | DONE |
| CP-09 | Integrated regression and design validation | CP-06, CP-07, CP-08 | DONE |
| CP-10 | PR evidence and staging acceptance | CP-09 | DONE |

## CP-01 — Profile contracts and persistence

- Add customer-authorized profile read and full-name update endpoints using the existing authentication dependency and browser-origin protections.
- Define allowlisted request/response models, bounded text fields, stable error codes and verified sign-in-method metadata. Reject direct writes to email, phone, Google identity, verification state, role and user ID.
- Keep `users.name` as the name source. Define a MongoDB customer profile document keyed by the existing user ID, with an address array, default references and revision. Prefer user ID as `_id` to use MongoDB's existing unique key.
- Initialize absent profile documents safely without rewriting existing customer records. Document any required index-contract additions and bootstrap implications.
- Extend `safe_user()` and auth-context refresh deliberately so name and linked-method changes appear consistently.

Acceptance: saved names survive a fresh read and sign-in; unauthenticated, unsupported-role and identity-field writes fail; no API exposes another customer's profile. Google-only, WhatsApp-only and dual-method profiles have accurate verified states.

## CP-02 — Saved-address APIs and defaults

- Implement add, edit, delete and default-reference endpoints against the authenticated customer's profile.
- Validate label, address line 1, optional line 2/landmark, city, state, six-digit PIN and India country. Bound field lengths and address-array size in the API contract and document the chosen limits before coding the interface.
- Use stable server-generated address IDs and revision-conditional writes, including safe first-document creation. Return a stale-revision conflict instead of overwriting concurrent edits.
- Update an address and its default references in one atomic document operation. Validate replacement defaults belong to the same customer and exist.
- Require explicit replacement or clearing of defaults on deletion. Preserve independent pickup and delivery defaults.

Acceptance: CRUD survives reload; another customer's address IDs are rejected; concurrent writes cannot lose changes or leave dangling defaults; first-address defaults reflect explicit submitted choices; deleting a default cannot silently select another address.

## CP-03 — Google identity linking

- Add authenticated Google-link start and purpose-specific handling in the existing callback. Store purpose, initiating user and initiating session with the OAuth transaction.
- Preserve state, nonce, PKCE, browser binding, expiration and atomic consumption. Validate the initiating session again at callback completion.
- Require verified Google email. Attach subject and verified metadata atomically to the current customer, preserving user ID, name, repairs and phone.
- Handle existing ownership and duplicate-key races. An identity already linked to the current user succeeds idempotently; another account's identity is rejected. Prevent replacing an already-linked Google identity through this flow.
- Return success, cancellation and safe failure feedback to Profile. Preserve normal Google login and privileged-account behavior.

Acceptance: a WhatsApp customer links Google and later signs in to the same user ID; conflicts preserve both accounts; expired, replayed, wrong-purpose, changed-session and invalid-claim callbacks cannot attach an identity or sign the customer into another account.

## CP-04 — WhatsApp mobile linking and replacement

- Extract reusable OTP challenge verification from `AuthService.verify()` while preserving login and registration contracts.
- Add authenticated request/verify endpoints with purpose-, session-, user- and target-number-bound challenges. Preserve normalization, provider restrictions, delivery status, cooldown, attempt limits and expiry.
- Ensure normal login challenges cannot authorize linking and linking challenges cannot register or sign in a different user.
- After successful verification, atomically attach or replace the phone with verified metadata and handle ownership races. Keep the old phone active until success.
- Cover stale concurrent replacement attempts with a conditional check on the original identity state.
- Session policy accepted by the owner on 2026-11-18: refresh the initiating session and revoke other sessions after replacement, using the existing `auth_epoch` mechanism. Coordinate identity and epoch updates so partial failures cannot transfer access or revive revoked sessions.

Acceptance: a Google customer gains WhatsApp access to the same account; verified replacement enables the new number and removes the old number from this account's login identity; conflicts, wrong codes and expired challenges preserve the original number. Replays and cross-session/purpose attempts fail. After replacement, the initiating session remains usable and other pre-existing sessions fail authentication. Existing OTP login/registration tests remain green.

## CP-05 — Profile page and navigation

- Add protected `/app/profile` inside CustomerShell and a Profile entry in desktop/mobile navigation.
- Reuse Logo and canonical tokens/components. Add the dashboard profile summary and Manage profile action.
- Build independently saving Personal details, Contact and sign-in, and Saved addresses sections, with loading, empty, pending, success and retry states.
- Display verified Google email read-only and describe available sign-in methods clearly. Refresh shared auth/profile state after changes.
- Make the approved Repairs action open `/repairs/new`; preserve access to existing repair history from the dashboard and existing list route.

Acceptance: navigation works on desktop and mobile; full-name edits appear in profile/dashboard; branding matches the existing component; Repairs opens the full charger form; protected routes and repair history remain accessible.

## CP-06 — Verification interfaces

- Connect Google linking and callback feedback to Profile, including conflict/cancellation recovery.
- Add the two-step mobile dialog with target number, WhatsApp wording, six-digit code, resend countdown and change-number action.
- Show active verified details while an attempt is pending. Disable duplicate submissions and handle expired sessions/provider failures safely.
- Provide accessible labels, error associations, focus management and clear sign-in summaries for all three account states.

Acceptance: each success updates the same profile; failures preserve displayed verified details; conflict messages match the approved design; keyboard users can complete and dismiss dialogs.

## CP-07 — Saved-address interface

- Build add/edit forms and compact address summaries with independent pickup/delivery defaults.
- Precheck both defaults only for the first address, allowing either to be cleared. Leave later addresses unchecked initially.
- Add delete confirmation with explicit replacement/clearing controls and stale-revision recovery.
- Refresh from persisted data after successful writes and surface save failures without discarding entered fields.

Acceptance: address operations persist after reload; independent defaults and same-address-for-both work; default deletion requires a valid explicit decision; narrow-screen forms remain usable.

## CP-08 — Repair form and snapshots

- Extend repair creation with optional saved pickup/delivery address IDs while keeping existing submissions without addresses valid.
- Resolve and verify ownership server-side, then copy location details into the repair document. Reject client-supplied authoritative snapshots.
- Preserve repair idempotency: a retry returns the original repair and snapshots even if a saved address has since changed or been deleted. Include selected IDs in request fingerprinting without recomputing historical snapshots for retries.
- Apply existing repair-response authorization to new address fields, including the charger-owner redacted view in `sanitize_repair()`.
- Insert optional address selectors within the existing full form. Prefill defaults, offer Choose later, and preserve charger fields, photos and selected addresses during an add-address detour.
- Include selected address summaries in review and the customer's repair details. Preserve charger selection, optional model, photo handling and WhatsApp consent behavior.

Acceptance: defaults prefill correctly; customers can submit without addresses; cross-account or deleted selections fail clearly; editing/deleting saved addresses leaves existing snapshots intact; ambiguous submission retries create one repair with its original snapshots; unrelated charger owners cannot read customer location details.

## CP-09 — Integrated verification

- Extend `backend/tests/test_auth_lifecycle.py`, `test_google_oidc.py`, repair tests and focused new profile/address tests. Exercise real MongoDB unique-index and conditional-write behavior in integration tests for identity races and concurrent address updates.
- Extend CustomerShell, CustomerHome and RepairNew tests and add profile/verification component tests.
- Add browser coverage for Google-only, WhatsApp-only and both-linked account states using deterministic provider fixtures. Verify same user ID, dashboard, repair history and addresses after switching sign-in methods.
- Check both themes at 320, 375, 768 and 1280 pixels, keyboard/focus behavior, error/empty/loading states and absence of horizontal overflow. Add representative Storybook states using canonical components.
- Run the repository's configured backend/frontend CI checks, frontend build and Storybook build. Record exact commands/results and fix regressions before requesting merge.

Acceptance: requirement acceptance criteria have passing automated coverage or a clearly identified staging/manual check. No secret, OTP or customer PII appears in committed fixtures or logs.

## CP-10 — Review and staging acceptance

- Update architecture/progress documentation with implemented collection/API contracts, compatibility constraints and evidence.
- Prepare reviewable PRs against `repair-mvp`, describing tests, identity-linking risks, index needs, rollout and rollback. Keep incomplete functionality out of exposed navigation until its dependencies are ready.
- After explicit merge approval and passing CI, let existing staging CD run. Verify frontend/backend revisions and service health using the established read-only checks.
- Validate durable profile/address saves, full repair submission with snapshots and both linked login methods on authorized staging test accounts. Coordinate user-completed Google sign-in and any authorized WhatsApp test delivery.
- Record staging evidence and rollback limitations: code rollback preserves added address data, while earlier code may not display it. Verify identity/session compatibility before choosing a rollback revision.

Acceptance: CI and staging evidence identify the tested commit; persisted data and both sign-in methods work end to end. Production promotion remains a separately authorized release.

## Review point

Implementation was authorized on 2026-11-18. The CP-04 session revocation policy was explicitly accepted on 2026-11-18. Existing-data cleanup and account consolidation remain outside this version's tasks.

Implementation notes: address fields are bounded at 40 characters for labels, 200 for each address line and 100 for city/state, with up to 20 addresses per customer. The MongoDB collection is `customer_profiles`, keyed by user ID in `_id`; no new secondary index or customer-data migration is required. Repair creation accepts optional address IDs and stores server-owned snapshots. An inline add-address dialog preserves repair drafts without browser storage of customer details.

The initiating session is retained through an ID and epoch recorded atomically with the new phone and account epoch in the user document; its stored session must still exist and be unexpired. Other sessions fail the account epoch check, and later account-wide epoch revocation invalidates the retention exception. New registration rejects unverified email input and directs customers to Google linking. Historical data remains untouched.

Validation results and the review/staging checklist are recorded in `validation.md`. CP-10 is complete: PR #69 was merged with owner approval, staging release evidence is recorded in validation.md, and the owner confirmed the remaining manual acceptance checks on 2026-11-19.
