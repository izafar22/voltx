# RushX 1.0 parked-feature inventory and release-readiness review

Reviewed 2026-11-06 from `archive/full-product-snapshot` and `develop` source, workflow config, and Render service/deploy metadata. This is a **source-based preflight**, not a completed release certification.

## Historical feature inventory

| Area | Historical source and evidence | Current develop state | Restoration and release decision |
|---|---|---|---|
| Charging sessions / QR / live charging | Archived `frontend/src/App.js` routes `/app/charger/:id`, `/app/live/:id`; `ChargerPage.jsx`, `LivePage.jsx`, `HistoryPage.jsx` | `frontend/src/config/features.js`: `charging:false`, `qrCharging:false`; routes gated | PARKED; retain code/history. Do not enable without backend auth, charging safety, session reconciliation and integration tests |
| Station discovery and map | `frontend/src/pages/customer/CustomerHome.jsx`, `frontend/src/components/StationsMap`; archived customer dashboard | `stationDiscovery:false`, `stationMap:false`; map conditional | PARKED; audit geolocation, permissions, data provenance and UX before reactivation |
| Wallet / top-ups | Archived `/app/wallet`, `WalletPage.jsx`; wallet code and owner dashboard | `wallet:false`; frontend route gated. Backend endpoints may remain callable | PARKED; frontend flags are not authorization; audit server API and money movement before reactivation |
| Owner network / payouts | Archived `/owner`, `OwnerDashboard.jsx`, endpoints such as `/owner/withdraw` | Source files still present; route not controlled by the listed feature flags | RELEASE RISK: inspect authorization and exposure; determine whether to explicitly gate/remove from 1.0, with regression tests |
| Legacy network admin | Archived `AdminDashboard.jsx` queries charger, owner, fault and withdrawal endpoints | Admin code persists and may mix network and repair administration | RELEASE RISK: identify repair-only admin UX and ensure network operations are not exposed accidentally |
| Repair enquiries and tracking | Archived `RepairNew.jsx`, `RepairDetail.jsx`, `RepairsList.jsx` | `repair:true`; updated repair and estimate/payment workflows | IN SCOPE, subject to end-to-end acceptance, auth, tenant/customer ownership and state-transition tests |
| Repair payments | `backend/PAYMENTS.md` and payment service/repository | Manual balance reconciliation and verified receipts, not an online payment gateway | IN SCOPE if explicitly accepted; verify money correctness, permissions, audit and no unapproved charge claims |
| WhatsApp lifecycle | `backend/WHATSAPP.md`, service/worker, catalog | Outbox, consent, event validation and template catalog documented | CONDITIONAL: verify Meta template approval, live env and worker deployment before claiming active notifications |

### Important distinction
The archived `main` code contains charging/network functionality, but **the repair-focused `develop` also retains many underlying components and backend routes**. Frontend feature flags alone are not an access-control or deployment boundary. A production readiness gate must inspect backend permissions and reachability, not merely hidden navigation.

## Render deployment audit (read-only)
- Production-facing backend service `voltx-backend` (`srv-daa87jgn74is73a4rv6g`) uses `repair-mvp`, auto-deploy enabled, root `backend`. Last observed live deploy: `ab3fff987197aa73c4fb31cbb178fc56d38d912e` (OTP integration).
- Production-facing frontend static service `voltx` (`srv-daaa1aoae00c73a70g70`) uses `repair-mvp`, auto-deploy enabled, root `frontend`. Last observed live deploy: `946e55f545962798dc94a63e77b29c6d8154cf03` (workshop hero).
- OIDC staging frontend/backend use separate feature branches with auto-deploy disabled.
- Render branch configuration **has not been changed**. Verify current deploys again immediately before release and privately check domains, secrets, database and worker configuration.

## CI and operational review
- `.github/workflows/tests.yml` runs on push/PR, Mongo 8 on Ubuntu 22.04, backend pytest, frontend Jest/build, Playwright public pages and Storybook checks.
- These commands were inspected but **not executed in this audit**. Obtain passing CI on the exact candidate SHA.
- `backend/PRODUCTION_BOOTSTRAP.md` describes an operator-controlled production Mongo index/bootstrap procedure; it must not be run on a populated database or without explicit approval. The runbook's claims do not establish current production DB state.
- No independent evidence yet that a WhatsApp outbox worker is running in production. Confirm worker process, retry behavior, Meta approval and opt-in before enabling notifications.

## Blocking release gates
1. Decide whether network admin and owner dashboard/routes should be disabled for repair-only 1.0; enforce server authorization regardless of frontend flags.
2. Test repair creation, duplicate submission, access isolation, admin state transitions, estimate approval, verified manual receipt, shipping and customer status views.
3. Verify WhatsApp OTP, consent, template approval, worker deployment, idempotency, webhook signature and disabled/test modes.
4. Confirm database/index compatibility and safe migration plan against actual target; no live writes as part of this review.
5. Run full CI on candidate commit and document exact test results, staging smoke checks, rollback commit and manual go/no-go approval.
6. Verify deployed frontend/backend commit pair and explicit `main`/Render cutover plan; no automatic branch switch.

## Proposed release path
- Keep `archive/full-product-snapshot`, `development`, `repair-mvp` intact.
- Resolve release blockers on separate feature/fix branches into `develop`.
- Only after the candidate baseline is approved, create `release_rushx_1.0` from a recorded `develop` SHA.
- Freeze features, validate release branch, obtain explicit authorization to promote to `main` and switch Render; record tag and rollback plan.
