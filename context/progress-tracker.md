# RushX progress tracker

Last reviewed: 2026-11-06. Statuses: DONE / IN_PROGRESS / PLANNED / PARKED / BLOCKED. A status describes available evidence, not a claim of production deployment.

| Status | Work item | Evidence / next action |
|---|---|---|
| DONE | Homepage workshop hero | PR #27 merged to `repair-mvp`; deployment not independently verified |
| DONE | WhatsApp OTP integration code | PR #26 merged to `repair-mvp`; check production runtime separately |
| IN_PROGRESS | WhatsApp lifecycle Utility templates | User configured eight production templates; screenshot showed six active and two in review on 2026-11-06. Recheck Meta status and exact template names/languages/parameters before integration |
| PLANNED | WhatsApp lifecycle backend wiring and tests | Audit `backend/services/whatsapp_service.py`, `backend/templates/whatsapp_utility_catalog.json`, outbox/worker and event triggers; avoid duplicate implementations |
| PLANNED | Release branching transition | Audit deployed SHA, `main`, `repair-mvp`, `development`, CI, Render, rollback; do not change deploy branch yet |
| PLANNED | Parked feature inventory | Trace historical branches/commits and record dependencies, ownership, restoration strategy |
| PARKED | Legacy non-repair MVP functionality | Preserve historic code; no automatic promotion into production |

## Update rules
Each meaningful PR updates affected rows, evidence links, verification date, and next action. Never mark DONE solely because a task was requested or code was drafted. Record release tag and deployed SHA only after deployment is verified. Do not include customer data or credentials.
