# WhatsApp estimate decisions — validation

Status: deployed and activated on staging. All three Meta templates are approved;
the first actionable estimate sends exposed the provider payload-length defect
documented below. The compact-token fix is locally validated and pending review/deploy.

## Evidence

- `python3 -m py_compile` passed for the changed backend modules and focused tests.
- `git diff --check` passed.
- Focused offline test: `5 passed` in `test_whatsapp_estimate_actions.py`.
- WhatsApp/lifecycle/auth/profile regression set: `189 passed, 1 deselected` across `test_whatsapp.py`, `test_lifecycle_v3.py`, `test_whatsapp_lifecycle.py`, `test_staging_lifecycle_payment_gate.py`, `test_whatsapp_estimate_actions.py`, `test_auth_lifecycle.py`, and `test_customer_profile.py`. The deselected test is the separately exercised real-Mongo profile concurrency case; this run used disposable mocked MongoDB.
- Tests use a mocked MongoDB/provider transport and synthetic phone, repair, estimate and QR values. They send no WhatsApp messages.

Covered behavior includes signed payload tamper rejection, ordered approval/decline buttons, webhook signature and duplicate handling, inbox redaction, current-state CAS application, retryable same-user identity-lease contention, post-commit recovery after expiry/progress, phone-replacement fencing, audit recording, exact reviewed QR header serialization, and text fallback while the QR gate is off.

## Remaining gates

1. Review the compact-token PR and exact-head CI, then deploy it to staging.
2. Repeat a real staging estimate send and button press through the allowlisted account.
3. Production activation and deployment require an explicit release approval and rollback plan.
## 2026-11-22 staging provider rejection follow-up

The first live actionable estimate jobs selected the correct template but Meta
rejected both with HTTP 400 / error 132005. A controlled replay returned
“Translated text too long”; body values were short while both signed quick-reply
payloads were 210 characters. The `rx2` format retains the bound repair, decision,
estimate fingerprint, destination and expiry with a 128-bit HMAC tag while reducing
the complete payload below 128 characters. Canonical Base64 and tamper regressions
pass. A fresh real staging send and button press remain required after deployment.
