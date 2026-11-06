# RushX 1.0 feature-isolation review

This branch introduces an explicit **backend** gate for parked charging/network APIs. `RUSHX_ENABLE_LEGACY_NETWORK` is disabled by default; only literal `true` enables those APIs. The flag is read per request. Do not set it in RushX 1.0 production. This is a release gate, not a substitute for authentication and role-based authorization.

## Protected routes
- Customer wallet, wallet top-up and transactions
- Station discovery, charger details and charging session APIs
- Owner network summaries, chargers, transactions and withdrawals
- Legacy network administration: summaries, chargers, owners, wallet adjustments, faults, withdrawals and sessions

Repair APIs, authentication, repair-specific admin payment/WhatsApp endpoints and general notifications are not intentionally gated. Frontend `/owner` now redirects to `/app`, and `/admin` to `/repairs`, retaining role checks.

## Open review blockers
1. **Legacy test compatibility:** existing tests assert wallet API responses in the default test environment. Update those fixtures to explicitly opt in to the parked network only for legacy tests, or replace expectations with disabled-by-default behavior. Do not merge until CI is green.
2. **Admin UX:** the old admin dashboard mixes charging/network and repair operations. Redirecting `/admin` to `/repairs` may remove existing administrative controls; verify all required repair actions are accessible in the release UI before merging.
3. **Audit all call sites:** check menus, login role redirects, owner/admin deep links, and server-side feature gates for unintended 404s.
4. Run full backend/frontend tests, Playwright and Storybook on the exact PR commit, then manual staging smoke tests of repair/estimate/payment/WhatsApp OTP.
5. Review any intentionally preserved network read endpoints outside the enumerated route families. No production environment variables, Render services or databases were changed.

This is a **draft implementation** awaiting tests and reviewer approval, not a certified production fix.
