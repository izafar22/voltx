# Privacy and data-deletion pages — implementation plan

Status: IMPLEMENTED LOCALLY, validation complete 2026-11-20. Requirements, copy, design and task plan were approved on 2026-11-20. No staging deployment, Meta publication or production deployment has occurred.

## P1 — Public content and routes

- [x] Add `PolicyPages.jsx` with the approved privacy and data-deletion content, semantic headings and email links.
- [x] Register `/privacy-policy` and `/data-deletion` as public routes and add their title, description and canonical metadata.
- [x] Render both pages through `PublicPage` and add their links to the active public footer.
- [x] Add scoped responsive policy-page styles using the existing public tokens and focus treatment.

Validation recorded 2026-11-20: focused `App.test.jsx` passed 33 tests. Both routes render without a session, use one `h1`, expose the approved email, remain linked from the footer and normalize trailing-slash requests to their canonical metadata/content path.

## P2 — Remove unused browser tracking

- [x] Remove the Emergent browser script and inline PostHog bootstrap from `frontend/public/index.html` while preserving theme initialization and Google Fonts.
- [x] Scan source and the optimized build for the removed runtime hostnames, project key, globals and recording configuration.

Validation recorded 2026-11-20: `npm run build` compiled successfully; source and `frontend/build` scans found no Emergent/PostHog runtime loader, API host, project-key prefix, browser global or session-recording configuration. `git diff --check` passed.

## P3 — Direct routing and sitemap

- [x] Add both policy paths to `SPA_EXACT` and `SITEMAP_STATIC`.
- [x] Extend route-contract and sitemap tests with both public URLs.

Validation recorded 2026-11-20: `test_studio_cms.py` and `test_seo_files.py` passed 35 tests with the loopback test environment. Direct routes, including trailing-slash variants, are recognized and the sitemap contains both policy URLs without exposing authenticated routes.

## P4 — Browser acceptance

- [x] Extend public Playwright coverage for direct navigation, refresh, metadata, footer links and keyboard focus.
- [x] Check 320, 375, 768 and 1280 pixel layouts in both themes for readable line length and no horizontal overflow.
- [x] Confirm the canonical RushX logo and business email are correct and no draft marker appears.

Validation recorded 2026-11-20: the clean-branch public browser suite passed 108 tests across all four widths, including dark-theme policy checks with axe WCAG 2 A/AA/2.1 AA rules. Generated screenshots were inspected at 320 and 1280 pixels. The optimized frontend build compiled successfully; source/build tracking scans and `git diff --check` passed.

Review regression recorded 2026-11-20: after normalizing trailing-slash routes, 33 focused frontend tests, 35 backend route/SEO tests, the optimized build and 16 policy-page browser checks passed.

CI stability regression recorded 2026-11-20: duplicate hosted runs exposed a pre-existing race in the lifecycle admin browser test, which could inspect the mobile menu before the authenticated shell rendered and then wait for a hidden desktop link. The test now selects desktop or mobile navigation deterministically from the configured viewport, matching the established customer-profile test pattern. All 32 lifecycle browser cases passed locally without changing application behavior or assertions.

## P5 — Staging and Meta prerequisite

- [ ] Open a dedicated PR describing tests, risks and context-documentation changes; keep it separate from WhatsApp runtime PR #75.
- [ ] After merge authorization, verify the automatic staging deployment and both public URLs.
- [ ] Record the staging-approved effective date in both pages if copy remains unchanged.
- [ ] Prepare the exact Meta privacy-policy and data-deletion URLs for a separate app-settings action.

Validation: staging URLs are public without login and match the approved copy. Meta publication, callback changes, production deployment and actual WhatsApp messages remain separately authorized and evidenced.

## Dependencies and order

P1 and P2 may be implemented together. P3 depends on the final paths. P4 follows P1–P3. P5 follows all automated checks and owner PR review.
