# RushX progress tracker

Last reviewed: 2026-11-12. Statuses: DONE / IN_PROGRESS / PLANNED / PARKED / BLOCKED. A status describes available evidence, not a claim of production deployment.

| Status | Work item | Evidence / next action |
|---|---|---|
| DONE | Homepage workshop hero | PR #27 merged to `repair-mvp`; deployment not independently verified |
| DONE | WhatsApp OTP integration code | PR #26 merged to `repair-mvp`; check production runtime separately |
| IN_PROGRESS | WhatsApp lifecycle Utility templates | User configured eight production templates; screenshot showed six active and two in review on 2026-11-06. Recheck Meta status and exact template names/languages/parameters before integration |
| PLANNED | WhatsApp lifecycle backend wiring and tests | Audit `backend/services/whatsapp_service.py`, `backend/templates/whatsapp_utility_catalog.json`, outbox/worker and event triggers; avoid duplicate implementations |
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
