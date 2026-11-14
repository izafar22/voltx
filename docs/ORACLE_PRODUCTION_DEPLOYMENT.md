# RushX production deployment — Oracle Cloud (verified 2026-11-10)

> Operational handoff for AI agents. This is an observed deployment snapshot, **not** authorization to modify production. Verify current state before acting.

## Services and routing

- Public frontend: `https://evchargerrepair.in`; alternate hostname `https://www.evchargerrepair.in`.
- Public API hostname: `https://api.evchargerrepair.in`.
- Oracle Cloud Ubuntu VM public IPv4 at verification: `168.138.113.64`.
- Nginx serves the compiled React SPA from `/var/www/rushx/frontend/` and proxies requests under `/api/` to `http://127.0.0.1:8000`.
- FastAPI backend listens on loopback port 8000. Its registered application routes already include the `/api/` prefix. **Preserve the URI prefix**: `proxy_pass http://127.0.0.1:8000;` (no trailing slash).
- Backend uses MongoDB Atlas; no database migration was performed as part of the frontend cutover.
- Enabled Nginx sites at verification: `default`, `rushx-backend`, `rushx-frontend`. Frontend site file: `/etc/nginx/sites-available/rushx-frontend`. Backend site file: `/etc/nginx/sites-available/rushx-backend`.
- The frontend Nginx site was configured with SPA fallback `try_files $uri $uri/ /index.html;` and a `/api/` reverse proxy. Certbot subsequently modified the frontend Nginx site to enable TLS and redirects; inspect the **current file** before changing it.

## DNS and TLS

- GoDaddy authoritative DNS was updated: A records `@`, `www`, and `api` point to `168.138.113.64` as of the verification. Prior frontend DNS pointed to Render: apex `216.24.57.1`, `www` CNAME `voltx-fdst.onrender.com`. Recursive caches may temporarily retain stale answers.
- Frontend Let's Encrypt certificate: `/etc/letsencrypt/live/evchargerrepair.in/fullchain.pem` and `privkey.pem`; covers apex and `www`; expires **2027-02-08** according to Certbot. Certbot reported automatic renewal scheduled.
- Existing API certificate is **separate**: `/etc/letsencrypt/live/api.evchargerrepair.in/`; expiration **2027-02-07** according to Certbot. Do not replace it during frontend maintenance.
- TLS verification from an external Mac returned `ssl_verify_result=0` for apex, `www`, and API. The `www` request returned HTTP 301; verify its redirect target if troubleshooting.

## Source, build, and release artifact

- GitHub repository: `izafar22/voltx`.
- Protected working integration baseline: `repair-mvp`; do not commit directly or merge/deploy without explicit approval. The frontend artifact was built from `release_20261110_version1.0.1` at SHA `cdfa5fe6d2122802e4193c2354b1681ebc2e30d3`.
- GitHub Actions workflow: `.github/workflows/frontend-release.yml` (`Frontend release artifact`). Node 22/Yarn builds the React frontend; packages `frontend/build` as `rushx-frontend.tar.gz` and uploads it as a GitHub Actions artifact ZIP. Do not build on the ~1 GB RAM Oracle VM unless specifically approved.
- Successful workflow run: `https://github.com/izafar22/voltx/actions/runs/42785327680`; artifact ID `13749641224` (artifact expiration was 2026-11-24). Historical evidence only, not a durable artifact store.
- The downloaded ZIP (`rushx-frontend-release.zip`) contained `rushx-frontend.tar.gz`. On the VM it was uploaded to `/home/ubuntu/`, unpacked into `/home/ubuntu/rushx-frontend-staging/`, verified for nonempty `index.html`, then **only compiled static assets** were copied to `/var/www/rushx/frontend/`. No source build was performed on Oracle.
- At deployment, static contents included `index.html`, `asset-manifest.json`, `theme-init.js`, `assets/`, and `static/`. Frontend HTML also referenced `https://assets.emergent.sh/scripts/emergent-main.js`; assess whether that external runtime dependency is needed before removing it.
- The backend's previously deployed release checkout was `/opt/rushx/app` on `release_20261109_version1.0.0`; **do not infer current backend commit or process state from this historical observation**.

## Observed smoke-test evidence (2026-11-10)

- `curl -H 'Host: evchargerrepair.in' http://168.138.113.64/` from an external Mac: HTTP 200.
- `https://evchargerrepair.in/`: HTTP 200 and valid TLS.
- `https://www.evchargerrepair.in/`: HTTP 301 and valid TLS.
- `https://api.evchargerrepair.in/`: HTTP 404 and valid TLS; a missing root route is not evidence of backend failure.
- `http://127.0.0.1:8000/openapi.json`: HTTP 200.
- `/api/stations` direct to FastAPI and via frontend Nginx: **both HTTP 401** without authentication, consistent with correct path-preserving proxy behavior.
- `/api/openapi.json` returned FastAPI-style 404 because OpenAPI is at `/openapi.json`, not `/api/openapi.json`.
- Frontend static assets returned HTTP 200 with correct MIME types: `/theme-init.js`, `/static/js/main.04353a85.js`, `/static/css/main.3e5ebf6c.css`.
- User reported the website renders smoothly in the browser without console errors.
- **Not yet verified end-to-end:** OTP authentication, authenticated session cookies, repair request creation, admin repair management, payment, WhatsApp notifications, complete redirect targets, automated renewal dry-run, monitoring and backup/restore.

## Operator checks (read-only by default)

```bash
sudo nginx -t
sudo systemctl is-active nginx
sudo certbot certificates
sudo ss -ltnp | grep -E ':80 |:443 '
curl -sS -o /dev/null -w '%{http_code}\n' -H 'Host: evchargerrepair.in' http://127.0.0.1/
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/openapi.json
curl -sS -o /dev/null -w '%{http_code}\n' -H 'Host: evchargerrepair.in' http://127.0.0.1/api/stations
```

A `401` on protected routes is not automatically an outage. Check application logs and real user flows before drawing conclusions. `nginx -t -c /etc/nginx/sites-available/rushx-frontend` is **not valid** because a site file is a `server` block, not a complete `nginx.conf`.

## Change controls and recovery

1. Read `AGENTS.md` and all six `context/` files before editing; inspect actual Git refs and live configuration.
2. Never assume this document matches today's running configuration. Capture `nginx -T`, deployed artifact hashes, release SHA, DNS answers, cert state, and backend health before making changes.
3. Do not alter the API vhost, production database, WhatsApp sends, DNS, TLS, or live deployments without explicit user approval. Preserve the `/api/` prefix and existing auth/cookie semantics.
4. For frontend releases, build in GitHub Actions, inspect the artifact, stage outside the webroot, validate assets, prepare a reversible release switch, test Nginx config, then reload gracefully **only when approved**.
5. Before changes, capture the current frontend assets/configuration for rollback and record the exact deployed commit/artifact. No automated rollback or fully versioned symlink-based release process was verified during this migration.
6. Keep Render history and parked functionality intact until explicitly approved for retirement. Do not delete prior services or configuration based on the successful Oracle smoke tests alone.

## Follow-up work

- Verify authenticated browser workflows: OTP, cookies, repair submission, admin dashboard, WhatsApp lifecycle.
- Confirm exact `www` redirect destination, current DNS propagation, and HTTPS redirect behavior.
- Audit the Emergent-hosted script, log/metric collection, certificate renewal dry-run, backup and restore, and deployment rollback process.
- Reconcile older `context/architecture.md` and `context/progress-tracker.md` statements about Render with this newer **operator-observed** Oracle deployment.
