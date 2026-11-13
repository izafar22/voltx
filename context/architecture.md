# RushX architecture (repository-grounded snapshot)

Reviewed: 2026-11-06 against selected files on `repair-mvp`. This is a partial architecture map; inspect source and operational configuration before changes.

## Logical flow
`React frontend (frontend/)` -> `FastAPI application (backend/server.py)` -> `MongoDB (Motor async client, DB_NAME environment setting)`.

Authentication is implemented in `backend/auth_service.py`, with Google OIDC-related production bootstrap documented in `backend/PRODUCTION_BOOTSTRAP.md`. Do not assume all operator provisioning or production migration steps have been executed.

WhatsApp: `backend/services/whatsapp_service.py` contains provider configuration, template catalog loading, webhook/outbox functionality. Catalog path: `backend/templates/whatsapp_utility_catalog.json`. Audit event-to-template mapping, workers and Meta Graph API environment configuration before implementation. Repair handlers should enqueue durable jobs, not send directly over the network.

Frontend public storytelling lives under `frontend/src/pages/public/storytelling/`; assets under `frontend/public/assets/visual-storytelling/`.

## Operational boundaries
The [Oracle production handoff](../docs/ORACLE_PRODUCTION_DEPLOYMENT.md) records the 2026-11-10 cutover. Public staging and production frontend and API responded over HTTPS on 2026-11-13. The active service units, deployment paths, database settings and deployed SHAs still require host verification. The proposed [unified Oracle workflow and rollout](../docs/ORACLE_CICD.md) use one CI artifact for both components. The legacy frontend workflow remains available. Production database bootstrap, index checks and admin provisioning require operator-approved runbooks.

## Before architecture changes
Trace actual call paths, data schemas, async workers, auth boundaries, failure/retry semantics, migrations and monitoring. Update this file with verified facts, diagrams and source links as they become known. Clearly mark assumptions and planned systems.

## Proposed frontend delivery (not active)

A manually dispatched GitHub Actions workflow on a `release_*` branch will build and test the React frontend on GitHub-hosted runners, require approval via a protected `production` environment, and deploy static files via non-root SSH to the Oracle Nginx frontend webroot. See `docs/ORACLE_FRONTEND_CICD.md` for prerequisites, rollback limitations and verification. No production configuration was changed by this proposal.

## Growth Studio blog and pages (added 2026-11-12, not yet deployed)

Blog posts and Studio pages are rendered on the server by FastAPI (`backend/services/studio_cms.py`), not by React: `/blog`, `/blog/<slug>`, `/sitemap.xml`, `POST /api/revalidate`, and a catch-all that serves Studio pages at any address, the React `index.html` (200) for the app's own routes, and a real 404 otherwise. Activation needs the Nginx routing and the `CMS_REVALIDATE_SECRET` backend variable described in `docs/STUDIO_CMS.md`. New React routes must also be added to `SPA_EXACT`/`SPA_PREFIXES` (a test enforces this). `/api/revalidate` is exempt from the browser-Origin guard; it authenticates with the shared secret.
