# RushX public education — issue #13

## Scope and architecture

Five public routes (`/`, `/services`, `/how-it-works`, `/about`, `/faq`) share a scoped public layout, service/FAQ/process content and the existing RushX Logo. Existing authenticated dashboards, repair forms, WhatsApp consent, API calls and backend are retained. The homepage is now public for signed-in users too; My account provides the existing role landing. The unused legacy Navbar/Footer are not mounted by the new public layout.

The branch starts at repair-mvp commit `4e225f0` and does not include OTP PR #12. Only the existing login success/redirect boundary changes: an allowlisted, tab-local sessionStorage destination (`/repairs` or `/repairs/new`) survives a Google full-page round trip or SMS flow. No user details or tokens are stored. The destination is consumed on completion, with ordinary role-home fallback; arbitrary URLs are rejected. Disabled browser storage falls back to the dashboard. Google OIDC protocol and backend callback remain unchanged.

Messaging follows issue #13: independent multi-brand service; assessment, acceptance and quotation required; Delhi NCR/Mumbai and eligible courier enquiries; Bengaluru planned only. No bulk/B2B workflow, invented contacts, reviews, authorizations, warranty promises or facility photography.

## Local evidence

- Frontend: 146 tests passed across 12 suites, including existing authentication, repair request and WhatsApp consent regressions.
- Production build: compiled successfully.
- Playwright: 32 passed on the production build at 320, 375, 768 and 1280px. All pages load directly, use distinct metadata, remain free of horizontal overflow, and link into the repair journey. Keyboard FAQ, mobile Escape/focus, service anchors, mocked SMS completion and simulated Google return are covered.
- Mobile and desktop screenshots reviewed. Representative screenshots are in `screenshots/`; all 20 page/width screenshots are produced by the browser suite and uploaded as CI artifacts.
- APIs are mocked in browser tests, external network blocked; screenshots show the font fallback. No real SMS, Google exchange, customer data, infrastructure or production database access.

## Metadata limitations

Each route updates title, description, canonical and Open Graph fields on navigation. Canonicals consistently use the issue's public identity, `https://evchargerrepair.in`, without query strings or anchors. The HTML fallback description describes repairs instead of charging wallets. This is the existing client-rendered React stack: crawlers that do not execute JavaScript will not receive distinct route metadata. There is no fabricated structured data or social image. Verify live crawler/social preview behavior separately; prerendering would require a separate hosting/build decision.

## Manual staging procedure (not performed against production)

1. Use a separately approved staging environment built from this branch, isolated test database and test accounts. Keep production auto-deploy/configuration unchanged. Do not merge PR #12 to test this branch.
2. Open and refresh all five public paths while signed out, signed in, and with session API temporarily unavailable. Public education should remain readable. Check mobile 320/375, tablet and desktop, keyboard-only navigation, visible focus, FAQ toggles, service anchors and all header/footer links. Confirm coverage and eligibility wording.
3. From the homepage choose Request a repair. Use a staging SMS test number, then verify arrival at `/repairs/new`. Repeat for registration and for Track a repair (`/repairs`). Direct sign-in without a pending enquiry should still use the role dashboard.
4. Repeat with a staging Google OAuth client and approved staging callback. Check successful sign-in, cancellation, failed callback/retry and session refresh. The same browser tab should return to its intended repair route; a new tab should have normal dashboard fallback. Automated tests simulate the callback session, not Google's exchange or real cookies through Render.
5. With test data only, submit one repair with WhatsApp consent unchecked and another checked, verify validation/status tracking and existing consent behavior. Use a sandbox WhatsApp provider; do not send customer messages. Confirm customer/owner/admin navigation and sign-out remain functional.
6. Inspect rendered canonical/description/Open Graph metadata and exercise the staging SPA fallback for deep links. Validate real-provider/cookie behavior and social previews before release. This work does not establish production OAuth, OTP or proxy readiness.

## Release/rollback considerations

No database migration, new runtime environment variable or production configuration change is required by this frontend change. Publishing remains a separate authorized action; merging repair-mvp can trigger existing auto-deploys and has not been performed. If later released and a regression appears, revert this feature's commit through review or restore the previous frontend release under the normal authorized rollout process; no data rollback is needed. Coordinate shared Login/App/CI edits when OTP PR #12 is eventually integrated, and rerun both suites after resolving overlaps.
