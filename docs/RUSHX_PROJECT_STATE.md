# RushX — Persistent Project State & Handover

**Checkpoint date:** 2026-11-14 (India)  
**Project:** RushX EV Charger Repair  
**Public website:** https://evchargerrepair.in  
**Repository:** https://github.com/izafar22/voltx  
**Document status:** Initial research-backed handover, generated from GitHub connector review and operator-reported deployment evidence. **Not committed to GitHub or deployed.**

> **READ FIRST IN EVERY NEW CHAT.** This document records a dated snapshot, not an automatically updated live state. Before any change, inspect the current Git branch/PRs, source files, live production state, and relevant runbooks. Never infer deployed code from Git HEAD alone. Explicit user authorization is mandatory for merges, deployments, production data/config changes, and live WhatsApp sends.

## 1. Immediate resume checkpoint

| Item | State / evidence | Confidence |
|---|---|---|
| Production release | **1.0.3**, exact SHA `144e1236f93b6dac1cc74aa8ce86403239f5ad1a` | Operator's successful cutover output, 2026-11-14 |
| Production frontend | `/var/www/rushx/frontend` → `/var/www/rushx/releases/144e1236f93b6dac1cc74aa8ce86403239f5ad1a` | Operator command output |
| Production backend | systemd `rushx-backend` WorkingDirectory `/opt/rushx/releases/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/backend`; Uvicorn loopback `127.0.0.1:8000` | Operator command output |
| Nginx | Config test and reload passed; frontend site and API host separate; Certbot TLS retained | Operator command output |
| Deployment smoke tests | **11/11** passed: `/`, `/login`, `/services`, `/repairs/new`, `/robots.txt`, `/blog`, `/sitemap.xml`, `/llms.txt` = 200; `/docs`, `/openapi.json` = 404; unauthenticated `POST /api/revalidate` = 401 | Operator command output |
| Customer repair workflow | **Working** | User acceptance statement; exact cases not independently logged |
| Growth Studio integration | **Working** | User acceptance statement; publish/revalidation details not independently logged |
| Growth Studio authorized revalidation | **PENDING confirmation**; do not mark complete until user confirms | User statement |
| Staging | **Not promoted** as part of 1.0.3; leave unchanged | Conversation evidence |
| Production safety | Existing previous release and backup retained; automatic rollback not exercised in cutover | Operator output and procedure |
| Current integration baseline | `repair-mvp` at `8de6d0b151c0ff92d3da5fbf08410eef6dc89f30` when checked; **2 commits ahead of deployed 1.0.3 SHA** | GitHub compare, 2026-11-14 |

**Next action:** Await user confirmation of an authenticated Growth Studio revalidation test (publish/update/unpublish, cache refresh, sitemap and `llms.txt` update). Then record result and decide whether to formally close release 1.0.3. Do not perform a new deployment to test revalidation.

## 2. Identity, product and scope

- **Customer-facing brand:** RushX. Historical repository/application name: Voltx; never present Voltx as current customer-facing brand.
- **Domain:** `evchargerrepair.in`; API hostname `api.evchargerrepair.in`.
- **Legal context from prior user discussion:** operating under GST trade name **hearth**, proprietor **Mohammad Afzal**. Confirm any legal text before publishing; do not treat a trade name as the same as the consumer brand.
- **Core proposition:** independent, multi-brand EV charger repair enquiries, assessment, diagnosis and coordination. Do not imply guaranteed repair success, manufacturer authorization, or nationwide coverage without evidence.
- **Current product:** public pages, authentication, customer repair request, administrative repair management, consent-controlled WhatsApp lifecycle, and Growth Studio CMS/SEO.
- **Parked legacy functionality:** charging-station maps, charging sessions, wallet and owner flows are present in historical product scope; preserve history but do not silently activate them in the repair-focused release.

Source: [`context/project-overview.md`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/context/project-overview.md), [`AGENTS.md`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/AGENTS.md).

## 3. Architecture and principal code locations

```text
Browser / React 18 SPA
    │ HTTPS https://evchargerrepair.in
    ▼
Oracle Ubuntu VM → Nginx + Certbot
    ├─ static frontend: /var/www/rushx/frontend (release symlink)
    ├─ /api/* → FastAPI 127.0.0.1:8000 (URI prefix preserved)
    ├─ /blog*, /sitemap.xml, /llms.txt, CMS pages → FastAPI
    └─ known SPA routes → static index.html

FastAPI backend (systemd rushx-backend)
    ├─ backend/server.py: app, repair/admin routes, API router
    ├─ backend/auth_service.py: OTP/session and Google OIDC flows
    ├─ backend/services/studio_cms.py: server-rendered CMS/SEO/revalidation
    ├─ backend/services/whatsapp_service.py: consent, events, outbox, webhooks
    ├─ backend/services/whatsapp_worker.py: separate sender worker (runtime status unverified)
    ├─ backend/services/payment_*: payment-related logic (runtime validation pending)
    └─ Motor/PyMongo → MongoDB Atlas (actual DB_NAME and access not exposed)
```

- **Backend:** Python FastAPI, Pydantic, Motor async MongoDB. Production systemd `EnvironmentFile=/etc/rushx/backend.env`; **never print values, tokens, secrets, DB URI or customer records**.
- **Frontend:** React 18, React Router, design tokens in `frontend/src/design-system/tokens.css`, Tailwind mapping, public storytelling components. Frontend is built on GitHub Actions/Node 22, not on the ~1 GiB Oracle VM.
- **Authentication:** OTP flows and Google OIDC. The repository bootstrap runbook stresses Google immutable `sub`, PKCE/state/nonce, stored role authorization, and operator-only admin promotion. Do not infer that every documented migration/enrollment has run in production.
- **Repair:** `POST /api/repairs` and administrative lifecycle; validate real API contracts from the deployed source before extending. Prior design included `REQUESTED → DIAGNOSIS → ESTIMATE → APPROVED/DECLINED → SHIPPED/RETURNED`, but current code may have richer states, including `AWAITING_SHIPMENT`; inspect current state machine rather than hardcoding this simplified list.
- **WhatsApp:** Meta Cloud API with explicit opt-in, durable embedded outbox and reconciliation, signed webhooks, idempotency, retries, receipts, dead-letter and manual recovery. A separate worker is documented; **whether it is active in production is not established**. No live message tests without authorization. See `backend/WHATSAPP.md` and `backend/templates/whatsapp_utility_catalog.json`.
- **Payments:** Modules exist; successful production payment flow is **not verified** in this checkpoint.

Sources: [`context/architecture.md`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/context/architecture.md), [`backend/server.py`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/backend/server.py), [`backend/WHATSAPP.md`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/backend/WHATSAPP.md), [`backend/PRODUCTION_BOOTSTRAP.md`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/backend/PRODUCTION_BOOTSTRAP.md).

## 4. Oracle infrastructure — verified and historical

| Area | Production | Staging / note |
|---|---|---|
| VM | `ubuntu@168.138.113.64`, hostname `rushx-vnic` | `ubuntu@137.23.43.117`, hostname `rushx-staging-vnic`; do not mix them |
| Backend | `rushx-backend.service`, Ubuntu user, loopback port 8000 | Previously reported inactive; **recheck before any staging task** |
| Frontend | Nginx `/var/www/rushx/frontend` symlink | No active frontend symlink at prior check |
| Site config | `/etc/nginx/sites-available/rushx-frontend` | Separate staging configuration not verified here |
| API config | `/etc/nginx/sites-available/rushx-backend` | Preserve API vhost |
| Environment | `/etc/rushx/backend.env` | Never copy production secrets into staging |
| TLS | Certbot-managed Let's Encrypt for apex/www and separate API certificate | Renewal status requires independent check |
| Resources | ~952 MiB RAM, 2 GiB swap, ~37 GiB free during preflight | Small VM: build off-host |

- Production host routes `/api/` with `proxy_pass http://127.0.0.1:8000;` **without trailing slash**, preserving `/api` prefix.
- Current 1.0.3 backend is selected through `/etc/systemd/system/rushx-backend.service.d/release-1.0.3.conf` (based on the successful cutover script and service output). The original unit remains at `/etc/systemd/system/rushx-backend.service` with WorkingDirectory `/opt/rushx/app/backend`; inspect the drop-in before changes.
- Nginx now routes `/blog`, `/blog/*`, `/sitemap.xml`, `/llms.txt`, and unknown CMS pages to FastAPI while retaining known SPA routes and static assets. Main domain blocks API documentation; API hostname remains separate.
- Historical Oracle deployment guide was verified 2026-11-10 and may contain obsolete statements about static-only routing and Render. This handover's 2026-11-14 operator evidence supersedes those **specific** observations, not the rest of the guide.
- Local operator Mac key path was `~/Downloads/ssh-key-2026-11-09.key` at cutover. This is a **path reference, not a credential**; never copy the key into a handover or Git.

Source: [`docs/ORACLE_PRODUCTION_DEPLOYMENT.md`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/docs/ORACLE_PRODUCTION_DEPLOYMENT.md).

## 5. Growth Studio CMS — deployed 1.0.3

- Site slug: `evchargerrepair`; site origin `https://evchargerrepair.in`.
- Routes: `/blog`, `/blog/<slug>`, `/sitemap.xml`, `/llms.txt`, `/studio-check`, arbitrary CMS page routes, `POST /api/revalidate`.
- Server-rendered HTML from `backend/services/studio_cms.py` is used for crawler/Studio compatibility; React does **not** render the blog content.
- Revalidation secret is in production backend environment as `CMS_REVALIDATE_SECRET` (64 hex characters); **value never recorded here**. Unauthenticated POST was verified to return 401; authenticated POST has **not yet been confirmed by user**.
- Cache: 5 minutes normal, 30 seconds after failed read, last-good-copy fallback, bounded to 2,000 entries. A CMS outage may return a graceful 200 page, so 200 alone is not proof of published content.
- `robots.txt` is static; sitemap and `llms.txt` are FastAPI-generated. Changes to React routes require synchronized CMS SPA allowlist (`SPA_EXACT`/`SPA_PREFIXES`) and SEO tests.
- Frontend assets: `studio-blocks.css`, `studio-blocks.js`, `studio/site.css`, `studio/tokens.css`; all verified in production archive.
- Source tests: `backend/tests/test_studio_cms.py`, `backend/tests/test_seo_files.py`. Before deployment, 35 focused tests passed in the isolated release venv with sanitized environment (operator output).
- Next CMS verification: authenticated publish/revalidate/unpublish, refreshed article and sitemap/llms content; confirm Studio *Check my website* status and Search Console/Bing submission separately.

Source: [`docs/STUDIO_CMS.md`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/docs/STUDIO_CMS.md).

## 6. Git branches, commits and release lineage (GitHub connector review, 2026-11-14)

**Do not assume `main`, `development`, `develop`, `repair-mvp` are equivalent.** Both `develop` and `development` currently appear in GitHub branch search. `repair-mvp` is the protected repair-focused integration baseline by user policy. New features/fixes branch from it, go through tested reviewed PRs, and are not directly edited. Release branches follow `release_<YYYYMMDD>_version<semver>`.

| Ref | GitHub compare against `a01d293` | Notes |
|---|---|---|
| `release_20261109_version1.0.0` | identical (0 ahead) | Historical backend checkout baseline |
| `release_20261110_version1.0.1` | 5 commits ahead | Public CTA/design and repair-form changes among compared files |
| `release_20261110_version1.0.2` | 8 commits ahead | Includes WhatsApp chat link and design-token related files |
| `release_20261114_version1.0.3` | **53 commits ahead** | Deployed SHA `144e1236...`; CMS/SEO, GitHub Actions, frontend, docs, tests and deployment scripts |
| `repair-mvp` | **55 commits ahead** | Integration baseline ahead of deployed 1.0.3 by **2 commits** |

**Important difference:** GitHub compare `144e1236... → repair-mvp` reports **2 commits**, changing `backend/auth_service.py`, `backend/server.py`, adding `backend/staging_safety.py` and `backend/tests/test_staging_safety.py`. These changes **are not in deployed 1.0.3**; do not describe them as production-live. The connector compare did not return individual commit messages for these two commits; fetch exact commits/PRs when planning next release.

Representative historical source milestones:

- 2026-08-30: original repair flow and dependency-fix commit messages appear on default-branch commit search (e.g. `7ff8d3901f` customer repair flow; `a68a67b906` repairs; `a9d10dd2f5` React 18/React Leaflet compatibility). These are **historical messages**, not independent verification of current deployment.
- PR #26 (WhatsApp OTP), #27 (workshop hero), #36 (CTA/model), #44 (WhatsApp visual), #51 (Growth Studio) are referenced in repository progress documentation. Their **current PR state is not verified here**; consult GitHub before relying on those older status descriptions.
- `feature/whatsapp-exact-brand-green` corrected exact `#25D366` token usage, white icon, responsive behavior; current production code should be checked if adjusting this control.
- GitHub branch search returned additional feature, docs, staging, release, archive and legacy branches. **Presence is not proof of merged/deployed status.** A full commit-by-commit historical inventory of all refs was not available from the connector's limited commit search; see audit limitations below.

Evidence: [GitHub compare deployed 1.0.3 to `repair-mvp`](https://github.com/izafar22/voltx/compare/144e1236f93b6dac1cc74aa8ce86403239f5ad1a...repair-mvp), [GitHub compare 1.0.0 to 1.0.3](https://github.com/izafar22/voltx/compare/a01d293...144e1236f93b6dac1cc74aa8ce86403239f5ad1a), [`context/progress-tracker.md`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/context/progress-tracker.md).

## 7. CI/CD, artifact and release safety

- `.github/workflows/oracle-frontend-deploy.yml` builds/tests/packages on pushes to `release_*`; uses Node 22/Yarn; packages `rushx-frontend.tar.gz`; uploads artifact named `rushx-frontend-${{ github.sha }}`.
- Deploy job only runs if repository variable `RUSHX_AUTO_DEPLOY_ENABLED == 'true'`. **Ad-hoc operator deployment was used for 1.0.3**; do not enable automatic deployment without explicit approval.
- 1.0.3 GitHub Actions build run was reported as `43516922685`, artifact ID `14081825226`; build succeeded, deployment job skipped.
- Verified frontend inner tar SHA-256: `9ef61c818b298db71f7a18f699bbbef5f15113e636b1720af47dd3b163968ce7`.
- Production preflight verified six backup checksum entries and tar assets. Production cutover smoke tests passed; **no rollback was triggered**, so rollback correctness remains unproven in a real failure.
- Cutover Mac scripts (operator-local, not assumed committed): `~/rushx-production-1.0.3.sh`, `~/rushx-set-cms-secret.sh`, `~/rushx-promote-1.0.3.sh`. Verify files exist before reusing. **Do not rerun the promotion script**: it is designed to refuse existing release/override and is not an idempotent upgrade path.
- Backup directory at cutover: `/var/backups/rushx/pre-growth-studio-20261113T214007Z` containing `backend.tar.gz`, `backend.env`, `nginx.tar.gz`, `frontend.tar.gz`, `frontend-release.txt`, `backend-commit.txt`, `SHA256SUMS`. Backup was checksum-verified but **not restore-tested**. **MongoDB Atlas data was not included.**
- Prior frontend symlink target: `/var/www/rushx/releases/ed1eb5a08da70cd1f2ce660f9a6f8ad85bd1ed1c`; prior backend working directory `/opt/rushx/app/backend` at `a01d293`.
- Never claim an automatic rollback can reverse database changes or all side effects; it only attempts process/config/artifact restoration.

Source: [Oracle frontend workflow](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/.github/workflows/oracle-frontend-deploy.yml), [`docs/ORACLE_FRONTEND_CICD.md`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/docs/ORACLE_FRONTEND_CICD.md).

## 8. Mandatory engineering and operational rules

1. **Read** `AGENTS.md`, then all six `context/` files in this order: `ai-workflow-rules.md`, `project-overview.md`, `architecture.md`, `code-standards.md`, `ui-context.md`, `progress-tracker.md`.
2. **Verify current refs and state**: repository, active branch, open PRs, relevant source/tests, and actual production/staging runtime. Docs may be stale.
3. **Protect `repair-mvp`**: no direct edits, no unsolicited merge; isolate changes in feature/fix branches; reviewed PR and tests required. Releases branch from the approved baseline and are pinned to exact SHA.
4. **No unapproved operations**: no merge, deploy, staging changes, production migration/data writes, DNS/TLS changes, live WhatsApp sends, or secret changes without explicit user authorization.
5. **Design system:** semantic tokens in `frontend/src/design-system/tokens.css` and Tailwind mapping; no arbitrary colors/spacing/shadows in JSX. Check light/dark and mobile/desktop.
6. **WhatsApp:** consent, E.164, sender separation, approved template name/language/ordered parameters, durable outbox, idempotency, signed callbacks, safe retries. No provider-level exactly-once claims.
7. **Quality:** applicable backend tests, frontend tests/build, browser regressions, security negatives, review diff and config, document actual outcomes and rollback.
8. **Security:** never include secrets, OTPs, customer personal information, token values or database URIs in chat logs, docs, commits or screenshots.
9. **Legacy/parked scope:** preserve old branches/features; don't merge broad legacy snapshots into repair MVP.
10. **Single-operation scripts:** user prefers one Mac-executable, fail-closed script with server identity checks, preflight, checksums, rollback strategy and explicit result. Read-only verification first when uncertain.

Sources: [`AGENTS.md`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/AGENTS.md), [`context/ai-workflow-rules.md`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/context/ai-workflow-rules.md), [`context/code-standards.md`](https://github.com/izafar22/voltx/blob/144e1236f93b6dac1cc74aa8ce86403239f5ad1a/context/code-standards.md).

## 9. Outstanding items and risk register

| Priority | Item | Why / evidence needed |
|---|---|---|
| P0 acceptance | **Confirm authorized CMS revalidation** | User explicitly pending; verify published content and sitemap/llms update after POST with secret, without exposing it |
| P1 operations | Test backup restoration and rollback procedure in isolated environment | Current backup checksums passed, restore/rollback not exercised |
| P1 security | Confirm WhatsApp worker status, production template approval, consent and notifications | Code/runbook present; runtime not independently verified |
| P1 production | Verify backup policy for Atlas, monitoring, alerts and certbot renewal dry-run | Not established by 1.0.3 smoke tests |
| P1 integration | Audit `repair-mvp` two newer commits and staging-safety changes before next release | They are not in deployed SHA |
| P2 SEO | Submit sitemap to Google Search Console/Bing and monitor indexing | Recommended by CMS guide; completion not verified |
| P2 hygiene | Update outdated repo `context/architecture.md`, `context/progress-tracker.md`, and deployment runbooks | They still refer to proposed/nondeployed Oracle/CMS and old Render state |
| P2 functional | Verify real WhatsApp notifications, payment flow, API-host behavior, admin permissions and negative tests | User confirmed customer workflow, not every protected subflow |
| P2 release process | Confirm protected-branch rules, tag policy, current PR states and CI gate behavior | Git refs and compare known; protection settings and tags not independently checked |
| P3 parked scope | Inventory all legacy branches/features and recovery dependencies | Repo context explicitly calls historical inventory incomplete |

## 10. Evidence, scope and limitations of this handover

**Directly reviewed via connected GitHub:** branch search; commit search (default branch); comparisons `a01d293` to release refs and `144e1236...` to `repair-mvp`; files `README.md`, `AGENTS.md`, six `context/` files, `backend/server.py`, `backend/requirements.txt`, `backend/WHATSAPP.md`, `backend/PRODUCTION_BOOTSTRAP.md`, `docs/STUDIO_CMS.md`, `docs/ORACLE_PRODUCTION_DEPLOYMENT.md`, `docs/ORACLE_FRONTEND_CICD.md`, `.github/workflows/oracle-frontend-deploy.yml` at deployed SHA. These substantiate structure and **aggregate** change sets.

**Not completed:** a full per-commit review of every branch and merged PR; a line-by-line diff audit of all 53 release commits; a live server SSH session by the assistant; Atlas data verification; independent authenticated CMS revalidation. Connector commit search surfaced only a limited default-branch history, so this document must **not** be described as a complete chronological commit audit. The compare API reported commit counts and changed files, not all individual messages.

**Operator-reported evidence:** production preflight, checksums, service config, 11/11 smoke tests, release symlink and systemd working directory, customer workflow and Growth Studio acceptance. Treat as credible user-provided observations, not a continuously refreshed monitor.

**Historical documentation conflicts:** older context files mention Render as production and Oracle/Growth Studio as proposed. They were accurate as of their older review dates but are stale relative to the 2026-11-14 cutover. `context/ai-workflow-rules.md` also proposes an older `release_rushx_1.0` naming convention, whereas the user's operative policy and actual branches use `release_<date>_version<version>`. Follow the user's current policy until docs are reconciled in a reviewed PR.

## 11. New-chat resume protocol

Paste this into a new chat in the **RushX EV Charger Repair ChatGPT Project**:

> Continue RushX from the attached `RUSHX_PROJECT_STATE.md`. Read the dated checkpoint first, then GitHub `AGENTS.md` and all six `context/` files, and inspect the latest relevant commits/PRs. Distinguish deployed production SHA from current `repair-mvp` HEAD. State (1) production version and verification date, (2) completed work, (3) pending work, (4) risks, and (5) the next safe action. Do not change GitHub, staging, production, secrets, or live data without explicit authorization. Update this handover only with evidence, and mark assumptions.

**At the end of each work session:** update the checkpoint date, exact SHA/ref, changed files/PRs, tests and results, deployment status, rollback/backup state, unresolved items and next step. Keep a copy in the ChatGPT Project; optionally commit a reviewed copy to GitHub through a docs PR. Neither location updates itself automatically from a chat.

---

**End of initial handover — 2026-11-14.**
