# RushX phone-first authentication and SMS release guide

## Delivery contract and configuration

RushX creates, hashes, expires, throttles and consumes OTP challenges in the
existing MongoDB auth collections. MSG91 only delivers that exact six-digit code.
We deliberately use the **SMS** API, not MSG91 SendOTP, Widget, Verify or Retry.
No second OTP verification authority or customer identity database is introduced.

Official API reviewed 2026-11-03:
[Send SMS](https://docs.msg91.com/sms/send-sms). The live documentation's embedded
API specification describes POST `https://control.msg91.com/api/v5/flow`, an
`authkey` header, and JSON `template_id`, `short_url`, and `recipients` containing
`mobiles` (country code, no plus sign) and case-sensitive template variables.
Its documented acceptance response is HTTP 200 with `type: success` and a
nonempty `message` request identifier. The adapter validates these fields and
never exposes provider diagnostics, codes, keys, recipient numbers or bodies.
Provider acceptance is not a delivery receipt; the UI says "Code requested".
HTTP rejection, malformed response and network/timeout errors fail closed and
consume the undelivered challenge. No automatic send retries occur because a
lost response can follow an accepted SMS.

The current SMS schema does not document a sender body parameter. The approved
sender, DLT content template and principal entity are bound to the MSG91 template.
`MSG91_SENDER_ID` is required deployment metadata (six letters) and must match
that approved binding. It is deliberately not sent as an invented API parameter.
The adapter cannot remotely prove this binding: verify it in MSG91 before release.

### Render checklist — configure only after separate rollout approval

| Name | Required value / source |
| --- | --- |
| `APP_ENV` | `production` on HTTPS staging and production |
| `OTP_MODE` | `provider` |
| `EXPOSE_DEMO_OTP` | `false` |
| `SMS_PROVIDER` | `msg91` |
| `MSG91_AUTH_KEY` | Private scoped MSG91 SMS auth key |
| `MSG91_TEMPLATE_ID` | Approved MSG91 SMS template ID |
| `MSG91_SENDER_ID` | Approved six-letter DLT sender configured on that template |
| `MSG91_OTP_VARIABLE` | Exact case-sensitive OTP variable, e.g. `otp`; cannot be `mobiles` |
| `JWT_SECRET`, `MONGO_URL`, `DB_NAME` | Preserve existing production identity/session configuration |
| `CORS_ORIGINS` | Explicit HTTPS frontend origins; production includes `https://evchargerrepair.in` |
| `GOOGLE_*` | Preserve working client/secret/exact callback configuration |

Incomplete/unknown SMS configuration yields 503 while Google remains available.
No provider key is required for CI or local demo mode. `.env.example` contains
placeholders only. Never put secrets in `REACT_APP_*`, commits, screenshots or logs.
Do not enable HTTP body/header debug logging or export credential-bearing HAR files.
Outbound HTTPS is fixed, redirects/proxy environment inheritance are disabled,
and connect/read/write/pool timeouts are explicitly bounded (3/10/5/3 seconds).

### MSG91 / Indian DLT setup — human account owner required

1. Complete the required business/KYC, DLT principal-entity and sender/header
   registrations with the approved business details. Do not substitute invented IDs.
2. Register the authentication/service content template with the appropriate DLT
   category. Keep the wording exact and use one dynamic six-digit-code variable.
   Do not put WhatsApp marketing/notification consent in an authentication SMS.
3. Create/map that approved content template, sender and PE ID in MSG91 SMS.
   Select the approved active/default version; confirm it is **Verified by DLT**.
   The MSG91 SMS template ID and DLT content-template ID are distinct.
4. Confirm the variable's exact spelling/case and the configured sender match.
   Keep remaining text static; this adapter supplies only one OTP variable.
5. Create a scoped auth key, confirm account credit and sender eligibility, and
   apply appropriate provider-side access restrictions. Supply it privately.
6. Only after approval, test one owned/allowlisted staging recipient and inspect
   provider delivery results. A 200 acceptance response alone does not establish
   carrier delivery. No automated test calls MSG91 or sends real SMS.

Official setup references: [SMS integration](https://msg91.com/help/api/how-can-i-integrate-sms-api),
[DLT template mapping](https://msg91.com/help/dlt-registration-in-india/map-sms-content-template-on-msg91-api-panel).

## Identity, security and consent

- Existing login/registration/session APIs remain. Phones normalize to Indian
  E.164. Secure generation, HMAC storage, five-minute expiry, five attempts,
  single consumption, cooldown and shared MongoDB phone/IP counters remain.
- `/api/auth/phone/request-otp` and `/api/auth/phone/verify-otp` require an active
  customer session and the existing trusted Origin guard. Linking challenges
  are bound to purpose and user ID. Login challenges cannot link a phone and
  linking challenges cannot log in or bind another customer.
- A Google customer proves their number before an atomic compare-and-set on their
  existing user document. The partial unique phone index arbitrates races.
  An already-owned phone returns 409 **after verification**, without merging
  accounts, moving repairs/wallets, or disclosing the other account. The recovery
  path is signing in with the original number or contacting RushX support for a
  reviewed ownership-recovery process; there is no automatic merge/recovery API.
- Already verified phones cannot be changed through this endpoint. Historical SMS
  customers with old sessions may verify only their existing assigned number.
  Owner/admin identities continue using SMS login; phone linking cannot grant roles.
- Successful OTP login/registration/linking stamps `phone_verified_at`; `/auth/me`
  exposes only a derived `phone_verified` boolean. No bulk backfill assumes that
  legacy phone values have been verified. No identity or repair migration is needed.
- New WhatsApp opt-ins require a verified valid account phone. Old repair consent
  snapshots, delivery destinations and outbox semantics remain unchanged. Existing
  unmarked sessions must prove their phone before a new opt-in; existing valid SMS
  logins establish that proof automatically. Linking never checks the consent box.
- Customer account phone verification is available at `/app/phone` and inline on
  `/repairs/new`. Inline verification preserves the in-progress repair form.
- Intended local routes survive SMS login and Google navigation. Only an allowlisted
  relative path is stored in sessionStorage; no JWT, registration token or OTP is
  persisted in browser storage. Existing protected routes still enforce role access.

## Safe staging and rollback — procedure only, not executed on production

Use the feature branch on a separately approved staging origin, isolated database
and fresh JWT secret. Never run integration tests against production or use its
MongoDB credentials. Use synthetic customer/Google fixtures and mocked SMS first.
For real provider staging, use provider mode, approved credentials/template, HTTPS,
matching CORS and Google callback settings and only an owned/allowlisted recipient.
Keep WhatsApp and simulated payment operations disabled. Mirror the `/api/*`
rewrite before the SPA fallback. Preserve callback queries, Origin/Cookie,
Set-Cookie/Location and no-store headers; verify them in a live staging browser.
The local Playwright suite cannot prove Render's live proxy or Google's client setup.

Verify: existing SMS and Google sessions; new customer name-only registration;
wrong/expired/exhausted codes; resend cooldown; one consumption under concurrency;
phone conflict and account-history preservation; inline Google phone verification;
explicit unchecked WhatsApp consent, repair submission and subsequent repair history;
Google's retained destination and server-side logout. Confirm no secrets in logs.
Record only boolean checks, aggregate outcomes and synthetic screenshots.

Before rollout, review a tested fallback build and account for Render auto-deploy
on `repair-mvp`. No merge/deploy/configuration changes are authorized by this guide.
Preserve the partial phone/provider indexes, users, verification markers, wallets,
repairs and existing consent/outbox records on rollback. Do not restore a full
unique phone index, delete phone-less users, fabricate phones, auto-link identities,
or restore an older database snapshot over newer activity. A compatible rollback
must retain Google and phone-optional session/data support; Google-only users have
no SMS fallback until they link a phone. Prefer a reviewed forward fix or a
compatible application fallback. Hide/disable new entry points only through an
approved release/configuration action. Missing/revoked SMS configuration fails
closed and leaves Google available. Do not weaken demo/Origin/role restrictions.

## Repeatable validation and visual evidence

All backend runs must explicitly set `MONGO_URL` to a disposable local server and
`DB_NAME` to a disposable test database; the repository's ignored local `.env` may
reference a live cluster. Never import/start the production server against it.
Run local MongoDB and the demo API with explicit test-only environment:

```sh
cd backend
MONGO_URL=mongodb://127.0.0.1:27019 DB_NAME=rushx_otp_local \
JWT_SECRET=local-test-secret-at-least-thirty-two-characters \
APP_ENV=test OTP_MODE=demo EXPOSE_DEMO_OTP=true \
CORS_ORIGINS=http://localhost:3000 venv/bin/uvicorn server:app --port 8001
```

In another terminal run pytest with those same variables plus
`REACT_APP_BACKEND_URL=http://localhost:8001`. Do not omit the explicit local
MongoDB settings. Full frontend validation:

```sh
cd frontend
CI=true npm test -- --watchAll=false --runInBand
npm run build
cd e2e
npm ci
npx playwright install chromium
npm test
```

Playwright serves the production build on loopback only, mocks every API/SMS/
Google flow, blocks external browser requests and checks 320/375/768/1280px.
It captures phone-entry, OTP and successful-login screenshots under
`frontend/e2e/test-results/`. CI uploads that synthetic evidence as an artifact;
no HAR/trace with auth data is recorded. Browser tests do not contact the live API.

Remaining operational blockers: real MSG91 credentials, approved sender/DLT/SMS
mapping, credit/permissions, owned-recipient delivery acceptance, and live HTTPS
staging/provider/Google/proxy verification. Implementation and automated tests use
mocks until those are supplied; no real customer SMS has been sent.

The IP throttle intentionally uses ASGI `request.client`, not untrusted browser
forwarding headers. During HTTPS staging, verify the real client-IP provenance
through Render's rewrite/proxy chain. Configure trusted proxy handling only for
verified infrastructure addresses in a separately approved rollout; never trust
arbitrary `X-Forwarded-For`. Shared/NAT proxy IPs may otherwise share the IP budget.
