# RushX deployment — free-tier rollout

## Existing services (do not duplicate)

- React static site: `voltx` — https://voltx-fdst.onrender.com — Render service `srv-daaa1aoae00c73a70g70`; root `frontend`; branch `repair-mvp`.
- FastAPI web service: `voltx-backend` — https://voltx-backend-lp42.onrender.com — Render service `srv-daa87jgn74is73a4rv6g`; root `backend`; currently on `main`, **not** the RushX `repair-mvp` code.
- Target domain: `evchargerrepair.in` managed by GoDaddy.
- MongoDB: separate Atlas database; do not migrate or overwrite an existing database without backup and explicit approval.

## CI/CD

`rushx-ci.yml` runs Python tests, Yarn frozen-install frontend tests and build on PRs/pushes to `repair-mvp`, and is reusable by the manual deployment workflow. **No production deploy on push** is configured by GitHub Actions.

`rushx-deploy.yml` runs tests first and then requires the GitHub environment `rushx-production` (configure required reviewers). It can be run manually **only from `repair-mvp`**. Configure:
- Environment secret `RENDER_API_KEY`: restricted Render API key. Never commit it.
- Environment variable `RENDER_BACKEND_SERVICE_ID`: `srv-daa87jgn74is73a4rv6g`.

Before enabling CD, change the **existing backend service** branch from `main` to `repair-mvp` in Render and disable Render auto-deploy for both services if GitHub Actions is to be the sole deployment controller. **Do not make this change before resolving production gates.** The existing frontend currently has Render auto-deploy enabled and has already published the merged RushX UI. A GitHub Actions deployment request is not proof of health: inspect Render deploy status and run smoke tests.

### Critical prerequisites (not yet completed)

1. Review `backend/PREMERGE_SAFETY.md`, Issues #6/#7 and outstanding Python/Yarn advisories. Do not launch publicly without a security decision.
2. Validate the backend's production environment variables without disclosing secrets; ensure real `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, auth environment, CORS, index permissions, and backups. Use a **separate** database for testing.
3. Keep WhatsApp sending disabled; a free Render web service can sleep, so a continuously running outbox worker is **not guaranteed**. Design/test an externally scheduled or otherwise reliable processing mechanism before enabling WhatsApp.
4. Keep mock payments and simulated finance disabled outside development/test.
5. Frontend uses relative `/api` and cookies. Configure a Render static-site proxy/rewrite for `/api/*` to the backend, with correct cookie/auth behavior; ensure SPA fallback does not shadow `/api`. Configure through Render dashboard or API; this repository does not currently control Render rewrite rules.
6. Set custom domain in Render, then follow the exact Render-provided GoDaddy DNS instructions. Preserve MX/TXT mail records and verify HTTPS. Do not guess A/CNAME values.
7. Verify API health, login, repair creation, estimate, payment receipt, permissions, error paths, cold start, and mobile behavior before public access.

### Free-tier constraints

No paid upgrades. Expect idle backend cold starts, limited availability/resources, and no guarantee of continuous background processing. Free MongoDB Atlas capacity/backup constraints need explicit review. GoDaddy domain renewal, Meta messaging and other usage are not included in hosting cost.
