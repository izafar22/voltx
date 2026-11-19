# WhatsApp repair lifecycle updates — audit and design review

Status: AUDIT / DESIGN INPUT, not an approved design. Requirements must be finalized before choosing detailed contracts or implementation tasks. Audit date: 2026-11-19; source baseline repair-mvp 5206722. No runtime/Meta configuration was changed or live delivery tested.

## Existing implementation to reuse

- `backend/services/whatsapp_service.py`: consent, nine-event catalog, immutable snapshots, environment/sender binding, configuration validation, durable reconciliation, leased/fenced dispatch, throttling, bounded retries, ambiguous-delivery review, signed receipts, aggregate metrics and guarded single-job replay.
- `backend/services/whatsapp_worker.py`: separately invoked worker entrypoint; not started by FastAPI. Source alone does not establish that any worker service is installed/running.
- `backend/server.py`: durable request/status events, verified-payment integration, business-fact validation, consent withdrawal, admin metrics and replay endpoints. Existing status transitions and payment constraints must be respected unless explicitly changed by approved requirements.
- `backend/templates/whatsapp_utility_catalog.json`: nine proposed templates; local approval fields are unknown. Eight lifecycle templates are required by the existing global production validation; PAYMENT_RECEIVED is validated when used. Including all nine means its readiness must also be checked explicitly before activation.
- `backend/tests/test_whatsapp.py`, `test_whatsapp_lifecycle.py`, `test_whatsapp_mongo.py`, and payment tests: substantial mocked/integration coverage. `backend/WHATSAPP_VALIDATION.md` records historical runs, not results executed for this spec or provider approval.
- `frontend/src/pages/customer/RepairNew.jsx`: currently submits whatsapp_opt_in=false and displays disabled Coming soon copy. It then attempts an automatic REQUESTED -> AWAITING_SHIPMENT transition.
- `frontend/src/pages/customer/RepairDetail.jsx`: current repair status, estimate actions, history and consent withdrawal. The dashboard is the existing source of customer-visible progress.
- `backend/staging_safety.py`: currently rejects WHATSAPP_ENABLED=true or WHATSAPP_PRODUCTION_APPROVED=true in staging. The worker entrypoint does not currently call this shared validator; an authorized future test gate must cover the worker as well as API.
- `backend/whatsapp_otp_provider.py`: OTP shares sender/token/version settings with lifecycle code but uses its own authentication template. Preserve its working production and allowlisted staging flows.

## Source-grounded gaps and risks

1. Progress context described lifecycle wiring/tests as merely planned, but implementation and tests already exist. Work should complete/harden/integrate/verify that implementation rather than create a second outbox.
2. Activation is not just enabling a checkbox: shipping instructions could currently be enqueued immediately after submission. Technical-acceptance timing and actor permissions need an approved business decision.
3. consent_record validates number syntax, not current phone verification; dispatch rechecks the repair's consent snapshot, not its current account number. Customer-profile phone replacement therefore requires explicit notification consent/race handling.
4. Existing retry logic can deliver older events after later ones. PAYMENT_PENDING rechecks its balance; equivalent freshness policy for other actionable events needs review.
5. Enabling a worker can reconcile existing embedded events/jobs. A reviewed activation boundary and old-job handling must prevent unintended historical sends.
6. No live Meta template, account, sender, webhook subscription, worker service, outbound gates or queue contents were inspected for this spec. Existing dated template evidence and successful OTP authentication do not establish lifecycle readiness.
7. Existing templates have no dashboard URL parameters. Do not append new variables/buttons or promise one-tap links without verifying an approved template variant.

## Proposed template inventory (not live approval evidence)

| Event | Local proposed name | Ordered body parameters |
|---|---|---|
| REQUESTED | `rushx_repair_requested_v1` | customer_name, repair_number, charger_description |
| AWAITING_SHIPMENT | `rushx_awaiting_shipment_v1` | customer_name, repair_number, dispatch_address |
| RECEIVED_AT_VOLTX | `rushx_charger_received_v1` | customer_name, repair_number |
| ESTIMATE_SENT | `rushx_estimate_ready_v1` | customer_name, repair_number, estimate_total |
| CUSTOMER_APPROVED | `rushx_estimate_approved_v1` | customer_name, repair_number |
| REPAIR_COMPLETED | `rushx_repair_completed_v1` | customer_name, repair_number |
| PAYMENT_PENDING | `rushx_payment_pending_v1` | customer_name, repair_number, amount_due |
| SHIPPED_TO_CUSTOMER | `rushx_return_shipped_v1` | customer_name, repair_number, courier, tracking_number |
| PAYMENT_RECEIVED | `rushx_payment_received_v1` | customer_name, repair_number, verified_amount, safe_reference |

All local entries use en_US and proposed Utility category. Exact live name, locale, category, full body, components/parameter order and current status must be verified with authorized access before sends; no template edit/submission is authorized.

## Decisions for requirements review

| Decision | Recommendation | Status |
|---|---|---|
| Initial milestone set | Existing eight plus PAYMENT_RECEIVED, subject to its exact template approval | Asked owner; pending |
| Shipping instructions | Only after explicit RushX team acceptance; remove automatic transition and enforce API permission | Asked owner; pending |
| Old repairs and old jobs | No retroactive opt-in/backfill; audit and quarantine pre-activation backlog | Proposed; review with requirements |
| Verified phone changes | Pause affected repair notifications; never silently redirect; account remains usable | Proposed; detailed race/reconsent design pending |
| Exceptions and extra messages | Existing account/support handling in v1; new templates need separate approval | Proposed; review with requirements |
| Dashboard links | Use existing copy referring to the account; add links only if approved template supports them | Proposed; template audit pending |

## Design topics after requirements approval

Define consent capability/readiness contract and draft-preserving verified-phone journey; team acceptance state/actor and operator UI; account-consent races and dispatch boundary; event freshness/order/expiry; activation cutoff and job compatibility; narrow staging test gate applied to API and worker; supervision/health/observability; redacted live-template audit; rollout and rollback. Evaluate index/schema/config changes explicitly. Reuse canonical UI tokens and existing components.

Do not weaken the existing delivery-ambiguity/replay policy, verification-purpose separation, staging DB isolation or payment facts. Any proposed change must identify the exact source/test evidence and compatibility effects before design approval.
