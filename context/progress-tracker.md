# RushX progress tracker

Deployment policy agreed 2026-11-18 is recorded in `docs/DEPLOYMENT_REQUIREMENTS.md`. Staging CD is active; selected production promotion remains implementation work.

Deployment policy reviewed: 2026-11-18. Other work items retain their dated evidence. Statuses: DONE / IN_PROGRESS / PLANNED / PARKED / BLOCKED. A status describes available evidence, not a claim of production deployment.

| Status | Work item | Evidence / next action |
|---|---|---|
| IN_PROGRESS | Customer profile, linked sign-in and saved addresses | Spec recorded in PR #68. Implementation authorized 2026-11-18 on `feature/customer-profile`: profile/address APIs, Google/WhatsApp linking, session policy, customer UI and repair snapshots implemented; local validation passed: 398 backend tests, 173 frontend tests, 116 app browser checks and 151 Storybook checks; PR/CI review underway. PR #69 review fixes address atomic session retention, guarded asynchronous saves, stale drafts/defaults, navigation matching and stable repair retries. Staging acceptance follows separate merge approval. See `specs/customer-profile/tasks.md` and `specs/customer-profile/validation.md`. |
| IN_PROGRESS | Staging Google login configuration | Verified 2026-11-18. Existing staging client now includes current callback; missing settings installed securely on Oracle. Real Google login, reload, preserved repair destination, and cancellation checks pass. Next complete a fresh Google sign-in and verify callback completion and the repair destination after automatic staging deployment. See `docs/STAGING_GOOGLE_LOGIN_SPEC.md` |
| DONE | Automatic staging CD | Verified 2026-11-18. PR #65 merged; dedicated VM account and GitHub staging secrets configured. Run 44178531783 initially failed frontend checks due to Nginx traversal permissions and verified paired rollback. After installing the corrected helper, retry passed. Read-only SSH confirmed frontend and backend at 49acf600cddc29cf2caadd0d81cf25813b897b13; backend active. PR #66 records the corrected /var/www frontend path. See `docs/STAGING_CD.md` |
| PLANNED | Selected production promotion | Requirements agreed 2026-11-18 in `docs/DEPLOYMENT_REQUIREMENTS.md`; implementation pending |
| DONE | Homepage workshop hero | PR #27 merged to `repair-mvp`; deployment not independently verified |
| IN_PROGRESS | Repair workflow transparency | PR #83 is merged and staging deployment was independently verified at `765be006323b4d31a5165541f536e9b5e969cdd1`. A second motion pass on `codex/lifecycle-lively-motion`, informed by owner-provided HeyClicky website and Mac-app references, adds a single travelling lifecycle signal, responsive pointer parallax, a living central status presence, active-stage pulse and spring WhatsApp bubble while retaining transform/opacity rendering, pause semantics and reduced-motion support. Focused lifecycle tests and the production frontend build pass locally. Review, CI and staging reevaluation remain; production is unchanged. See `specs/repair-workflow-transparency/validation.md`. |
| DONE | WhatsApp OTP integration code | PR #26 merged to `repair-mvp`; check production runtime separately |
| IN_PROGRESS | WhatsApp lifecycle Utility templates | User configured eight production templates; screenshot showed six active and two in review on 2026-11-06. Recheck Meta status and exact template names/languages/parameters before integration |
| IN_PROGRESS | WhatsApp lifecycle updates | PRs #74 and #75 are merged and deployed to staging. Owner-authorized acceptance on 2026-11-21 recorded all eight positive-balance jobs delivered on first attempt, then paused the activation, stopped the worker and restored the default-off gates. Acceptance exposed the blanket staging financial middleware blocking the two repair-payment UI mutations; a narrow activation-, heartbeat-, consent- and recipient-bound hotfix is in progress. Fresh UI-only staging acceptance is required after its CI/merge/deploy. Production remains unchanged and separately gated. See `specs/whatsapp-lifecycle-updates/validation.md`. |
| IN_PROGRESS | WhatsApp estimate decisions and merchant QR | All three Utility templates were approved and both independent gates activated on staging on 2026-11-22. Live diagnosis found Meta rejecting the original 210-character quick-reply payload with error 132005; the compact authenticated `rx2` token fixes the provider limit and passes focused regressions. Next: review/merge/deploy the fix and repeat one real estimate-button acceptance. See `specs/whatsapp-estimate-decisions/` and `specs/whatsapp-lifecycle-updates/staging-acceptance.md`. |
| IN_PROGRESS | Public privacy and data-deletion pages | PR #76 merged at `c8f4fcc`; run 507 passed and deployed both staging components at that SHA. Both login-free pages render on staging, the sitemap contains their canonical production URLs and unused Emergent/PostHog runtime tracking is absent. Production and Meta app configuration remain unchanged. See `specs/privacy-and-data-deletion/`. |
| PLANNED | Release branching transition | Audit deployed SHA, `main`, `repair-mvp`, `development`, CI, Render, rollback; do not change deploy branch yet |
| PLANNED | Parked feature inventory | Trace historical branches/commits and record dependencies, ownership, restoration strategy |
| PARKED | Legacy non-repair MVP functionality | Preserve historic code; no automatic promotion into production |

| IN_PROGRESS | RX-001 / RX-002 frontend changes | Draft PR #36 from `repair-mvp`: Book Repair CTA via design-system variant and optional charger Model. Static diff checked; frontend tests, Storybook build and CI still require execution before merge. |

| IN_PROGRESS | Public WhatsApp click-to-chat link | Feature branch `feature/whatsapp-chat-link`: public pages link to business WhatsApp number +91 8528077908 with prefilled repair enquiry. Added component test; CI/browser behavior and production deployment not yet verified. This is separate from WhatsApp Cloud API/outbox. |

## Update rules
Each meaningful PR updates affected rows, evidence links, verification date, and next action. Never mark DONE solely because a task was requested or code was drafted. Record release tag and deployed SHA only after deployment is verified. Do not include customer data or credentials.

| IN_PROGRESS | Floating WhatsApp button visual refresh | `feature/whatsapp-button-visual-final`: 56px icon-only control, classic green background, white 32px icon, fixed 24px from bottom/right. CI pending; not deployed. |

| IN_PROGRESS | Exact WhatsApp brand green correction | `feature/whatsapp-exact-brand-green` from PR #44 merge: RGB token channels `37 211 102` mapped through Tailwind to exact `#25D366`. Playwright checks computed colour in both themes at all four configured widths, plus approved geometry, icon, shadow and hover. CI verification pending; production deployment held. Previous uncorrected 1.0.2 artifact must not be deployed. |

CI first run: exact colour and geometry assertions passed; all eight new cases caught computed `box-shadow: none` from the ambiguous arbitrary shadow class. Map the unchanged shadow token through a named Tailwind shadow utility and rerun all checks. Production remains on hold.

CI second run: shadow assertions passed; icon assertions exposed `.rx-public a { color: inherit }` overriding the link foreground. Apply the existing white semantic colour directly as SVG fill, preserving the approved icon colour across themes. Rerun full CI; deployment remains held.

| IN_PROGRESS | Approval-gated Oracle frontend CI/CD | `feature/oracle-frontend-cicd-approval`: manual release-branch workflow, GitHub production environment gate, non-root SSH deployment, staged build and backup/rollback. Requires review, CI, environment protection and VM account setup; no deployment performed. |

| IN_PROGRESS | Growth Studio blog, robots.txt, llms.txt, sitemap | `feature/growth-studio-seo` from `repair-mvp`: server-rendered `/blog`, posts, Studio pages at any address, `/sitemap.xml`, `/llms.txt`, `POST /api/revalidate`, static `robots.txt`. Studio publishes reach the sitemap and llms.txt through the update route. Verified 2026-11-12: `backend/tests/test_studio_cms.py` and `test_seo_files.py` pass locally (Python 3.12); evidence and CodeRabbit resolutions in PR #51 (https://github.com/izafar22/voltx/pull/51); CI pending. Not deployed: needs frontend + backend release, `CMS_REVALIDATE_SECRET` and the Nginx change in `docs/STUDIO_CMS.md`, then Studio's Check my website. |

| IN_PROGRESS | WhatsApp repair form layout hotfix (post-1.0.4) | `hotfix/whatsapp-consent-grid-layout` restores the prior two-column grid for the disabled Coming Soon checkbox/label after the 1.0.4 production screenshot showed severe text wrapping. Preserves `whatsapp_opt_in: false`. JSX regression assertion updated; unit tests/build and rendered layout intentionally not run at preparation time. PR review and release approval pending. |

| IN_PROGRESS | RushX 1.0.6 checkbox alignment hotfix | `hotfix/whatsapp-checkbox-alignment-1.0.6`: screenshot after 1.0.5 showed disabled WhatsApp checkbox lower than label. Remove `mt-1` and apply `self-start`; keep grid and consent opt-out. DOM regression assertion added; tests, CI and browser rendering not yet verified. Merge/release/deploy require separate approval. |
## 2026-11-22 — continuous staging WhatsApp follow-up

- Prepared an explicit continuous-staging lifecycle gate; the existing bounded
  1–120 minute acceptance window remains the default.
- Added a fail-closed exception for an operator-reviewed sole-proprietor merchant QR
  hosted under the isolated staging payment-asset path. Production behavior is unchanged.
- Submitted the actionable estimate, estimate-declined and balance-due QR Utility
  templates to Meta; all three were pending at the time of submission.

## 2026-11-23 — repair booking physical details

- IN_PROGRESS: `feature/charger-physical-details` adds required charger weight (kg)
  and longest-side length (cm) fields to the booking form. The API fields remain
  optional for existing clients and records. Focused frontend validation/payload
  tests (14) and backend persistence/bounds test (1) pass; the production frontend
  build also succeeds. PR review and staging acceptance remain; not deployed.
