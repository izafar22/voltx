# RushX architecture (repository-grounded snapshot)

Reviewed: 2026-11-06 against selected files on `repair-mvp`. This is a partial architecture map; inspect source and operational configuration before changes.

## Logical flow
`React frontend (frontend/)` -> `FastAPI application (backend/server.py)` -> `MongoDB (Motor async client, DB_NAME environment setting)`.

Authentication is implemented in `backend/auth_service.py`, with Google OIDC-related production bootstrap documented in `backend/PRODUCTION_BOOTSTRAP.md`. Do not assume all operator provisioning or production migration steps have been executed.

WhatsApp: `backend/services/whatsapp_service.py` contains provider configuration, template catalog loading, webhook/outbox functionality. Catalog path: `backend/templates/whatsapp_utility_catalog.json`. Audit event-to-template mapping, workers and Meta Graph API environment configuration before implementation. Repair handlers should enqueue durable jobs, not send directly over the network.

Frontend public storytelling lives under `frontend/src/pages/public/storytelling/`; assets under `frontend/public/assets/visual-storytelling/`.

## Operational boundaries
Production hosting has been discussed as Render, but current frontend host, Render deploy branch, active database name, secret settings, production release SHA and deployment topology require live verification. Never infer deployment from a merged PR. Production database bootstrap, index checks and admin provisioning require operator-approved runbooks.

## Before architecture changes
Trace actual call paths, data schemas, async workers, auth boundaries, failure/retry semantics, migrations and monitoring. Update this file with verified facts, diagrams and source links as they become known. Clearly mark assumptions and planned systems.

## Proposed frontend delivery (not active)

A manually dispatched GitHub Actions workflow on a `release_*` branch will build and test the React frontend on GitHub-hosted runners, require approval via a protected `production` environment, and deploy static files via non-root SSH to the Oracle Nginx frontend webroot. See `docs/ORACLE_FRONTEND_CICD.md` for prerequisites, rollback limitations and verification. No production configuration was changed by this proposal.
