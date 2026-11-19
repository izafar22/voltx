# RushX architecture (repository-grounded snapshot)

Reviewed: 2026-11-06 against selected files on `repair-mvp`. This is a partial architecture map; inspect source and operational configuration before changes.

## Logical flow
`React frontend (frontend/)` -> `FastAPI application (backend/server.py)` -> `MongoDB (Motor async client, DB_NAME environment setting)`.

Authentication is implemented in `backend/auth_service.py`, with Google OIDC-related production bootstrap documented in `backend/PRODUCTION_BOOTSTRAP.md`. Do not assume all operator provisioning or production migration steps have been executed.

WhatsApp: `backend/services/whatsapp_service.py` contains provider configuration, template catalog loading, webhook/outbox functionality. Catalog path: `backend/templates/whatsapp_utility_catalog.json`. Audit event-to-template mapping, workers and Meta Graph API environment configuration before implementation. Repair handlers should enqueue durable jobs, not send directly over the network.

Frontend public storytelling lives under `frontend/src/pages/public/storytelling/`; assets under `frontend/public/assets/visual-storytelling/`.

## Operational boundaries
Oracle production has independently selected frontend and backend releases. Use the read-only check in `AGENTS.md` to verify the active frontend release directory, backend working directory and service PID. See `docs/ORACLE_PRODUCTION_DEPLOYMENT.md` for the dated hosting snapshot. Production database bootstrap, index checks and admin provisioning require operator-approved runbooks.

On the Oracle staging VM, Nginx serves the frontend through `/var/www/rushx-staging/staging` and proxies the API to `rushx-staging.service`. The separate staging SSH check in `AGENTS.md` resolves the frontend release and reports the backend service state and working directory.

Staging CD is active as verified on 2026-11-18. The `deploy-staging` job follows passing mainline CI and deploys both components from its artifact through the installed staging-only SSH helper. The dedicated deployment account and GitHub staging secrets are configured. See `docs/STAGING_CD.md` for the successful run and rollback evidence.

## Before architecture changes
Trace actual call paths, data schemas, async workers, auth boundaries, failure/retry semantics, migrations and monitoring. Update this file with verified facts, diagrams and source links as they become known. Clearly mark assumptions and planned systems.

## Proposed frontend delivery (not active)

A manually dispatched GitHub Actions workflow on a `release_*` branch will build and test the React frontend on GitHub-hosted runners, require approval via a protected `production` environment, and deploy static files via non-root SSH to the Oracle Nginx frontend webroot. See `docs/ORACLE_FRONTEND_CICD.md` for prerequisites, rollback limitations and verification. No production configuration was changed by this proposal.

## Growth Studio blog and pages (added 2026-11-12, not yet deployed)

Blog posts and Studio pages are rendered on the server by FastAPI (`backend/services/studio_cms.py`), not by React: `/blog`, `/blog/<slug>`, `/sitemap.xml`, `POST /api/revalidate`, and a catch-all that serves Studio pages at any address, the React `index.html` (200) for the app's own routes, and a real 404 otherwise. Activation needs the Nginx routing and the `CMS_REVALIDATE_SECRET` backend variable described in `docs/STUDIO_CMS.md`. New React routes must also be added to `SPA_EXACT`/`SPA_PREFIXES` (a test enforces this). `/api/revalidate` is exempt from the browser-Origin guard; it authenticates with the shared secret.

## Customer profile implementation (production verified 2026-11-19)

`backend/customer_profile.py` implements customer-scoped profile and saved-address APIs. MongoDB `customer_profiles` uses the existing user ID as `_id`, with an address array, independent default references and revision-conditional atomic writes. Existing MongoDB `_id` uniqueness handles document creation races, so this feature adds no secondary index or existing-data migration.

Authenticated linking operations in `auth_service.py` and `google_oidc.py` bind verification to purpose, initiating session and user. Existing unique phone and Google-subject indexes reject conflicting ownership. Mobile replacement atomically stores the new phone, incremented account auth epoch and initiating session ID/retention epoch in the same user document. Authentication admits only that retained, live, unexpired session across the epoch change. A later epoch increment invalidates retention, and logout still deletes the required session record. No second session-document write or MongoDB transaction is needed. Normal login and linking consume distinct challenge purposes.

Repair creation accepts optional pickup/delivery address IDs, resolves them against the customer profile and embeds location snapshots. Existing idempotent retries return the original repair before resolving mutable saved addresses. Repair-response redaction also applies to the new location fields.

`/app/profile` uses CustomerShell and shared profile/address/verification components. The repair form adds optional selectors and an inline address dialog to retain its draft. Profile data is held in memory, not local storage. Staging acceptance is complete, including owner-confirmed provider/session checks. Production frontend and backend are both at `479d2ee1e7337bd3db46a898d7a6ffb53887a994` on `release_20261119_version1.1.0`, independently verified on 2026-11-19. Production retains `/etc/rushx/backend.env`; the backend uses a separate release virtual environment and `zz-release-1.1.0.conf` systemd override. See `docs/CUSTOMER_PROFILE_PRODUCTION_RELEASE.md` for CI, smoke checks and paired rollback evidence. Authenticated production profile/provider journeys were not exercised during deployment.
