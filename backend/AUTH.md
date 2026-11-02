# Customer authentication

The existing `/api/auth/*` lifecycle now uses challenges and cookie sessions.
Existing users, roles, wallets, transactions, charging sessions, and repairs are
retained. SMS customers are created after phone verification and registration;
Google customers are created after validated OIDC authentication.

## Local configuration (never commit `.env`)

```dotenv
APP_ENV=development
OTP_MODE=demo
EXPOSE_DEMO_OTP=true
CORS_ORIGINS=http://localhost:3000
```

Keep the existing `JWT_SECRET`, `MONGO_URL`, and `DB_NAME`. Restart the backend
after configuration changes. The frontend uses public configuration:

```dotenv
REACT_APP_BACKEND_URL=http://localhost:8000
REACT_APP_DEMO_AUTH=true
```

Restart CRA after changing its environment. Demo controls require the public
flag and a nonproduction build. Demo code responses require both backend demo
mode and `EXPOSE_DEMO_OTP=true`. Demo mode sends no SMS. Demo seed accounts retain
their roles; signup always creates a customer. Existing startup demo fixtures
are now gated by `OTP_MODE=demo` and the optional charger seed retains its own flag.

## Production dependencies

Set `APP_ENV=production`, `OTP_MODE=provider`, `EXPOSE_DEMO_OTP=false`, a strong
random `JWT_SECRET` (at least 32 characters), and explicit HTTPS `CORS_ORIGINS`.
There is deliberately no configured SMS vendor. `OtpProvider.send_otp(phone, code)`
is the integration boundary; inject a real implementation when constructing
`AuthService`. Until then, requests return 503 and do not pretend SMS was sent.
Provider mode generates random six-digit codes and never returns them or logs
them. Production startup rejects demo auth, weak secrets, and non-HTTPS origins.
Deployment should keep the frontend/API on the same site for SameSite=Lax cookies.
Cross-site deployments require a separate considered cookie/CSRF design.

## API contract

1. `POST /api/auth/request-otp` with `phone` returns `challenge_id`, `expires_in`
   and `resend_after`. Indian numbers normalize to `+91XXXXXXXXXX`.
2. `POST /api/auth/verify-otp` requires `phone`, `challenge_id`, and `otp`.
   Existing users receive a session cookie and safe `user` profile. Unknown phones
   receive `registration_required` and a ten-minute scoped registration grant.
3. `POST /api/auth/register-customer` uses `Authorization: Bearer <registration grant>`
   with `name` and optional `email`. No client role or phone is accepted. The grant
   is consumed on successful account/wallet creation. Concurrent retries cannot
   create duplicate accounts/wallets; completed grants require signing in again.
4. `GET /api/auth/me` returns only allowlisted profile fields.
5. `POST /api/auth/logout` revokes the session and clears the cookie.

Auth responses use `Cache-Control: no-store`. Authentication validation errors
never echo request input. Registration grants stay in frontend memory only.

## Session and CSRF protection

The `access_token` cookie is HttpOnly, host-only, SameSite=Lax, path `/`, and
Secure in production. Sessions expire after 24 hours with no silent refresh.
JWTs contain expiry, subject, role, purpose, and a random session ID. MongoDB
session records allow immediate logout revocation; every protected request also
checks the user's current role/status. Disabled users cannot sign in or use
existing sessions. Bearer session JWTs are no longer accepted or returned.
The frontend removes legacy `ev_token` and restores the cookie via `/auth/me`.
Existing browser sessions must sign in again once; identity and balances do not
change. Query caches are cleared between authenticated users.

Every unsafe API request (including login/signup/logout) must carry an exact
trusted `Origin`. Missing and untrusted origins receive 403. CORS is configured
with specific origins and credentials enabled, never `*`. Non-browser clients
must provide an allowed Origin plus their cookie. Reverse proxies should preserve
Origin and only trust forwarded client-IP headers from known proxy addresses.

## OTP protections

Challenges contain an HMAC-SHA256 hash bound to the challenge ID, phone and OTP;
no plaintext code is persisted. They expire in five minutes, are single-use,
and reserve attempts atomically (maximum five). New challenges invalidate older
ones for that phone. Resend cooldown is 60 seconds; phone requests are limited
to five/hour and client IP requests to thirty/hour using atomic MongoDB counters.
429 includes Retry-After for request throttling. Provider delivery errors invalidate
the challenge. These pragmatic limits may need tuning for real traffic behind NAT.

## Indexes and migration

Startup first audits normalized valid phones for collisions before changing any
phone. Collisions fail startup with a generic diagnostic; no accounts are merged
or deleted. Resolve conflicts operationally with the account owner, not by resetting
financial/history data. Malformed legacy fixtures are preserved untouched but
cannot authenticate until their phone is corrected to a valid Indian mobile.

Unique indexes: `users.phone` (partial: string values only),
`users.(auth_provider, auth_subject)` (partial: both string values),
`users.user_id`, `wallets.user_id`.
TTL indexes on `expires_at`: `auth_challenges`, `auth_limits`, `auth_registrations`,
`auth_sessions`, `auth_google_transactions`. Additional lookup index: `auth_challenges.phone`.
Index conflicts/duplicates fail safely without deleting documents. The known full
unique single-field phone indexes are replaced only after the partial unique
phone index exists; other indexes are retained.
Run migration during a maintenance window (stop old writers) before rolling out
new backend workers. Future phone-writing features must use `normalize_phone`.
TTL cleanup is asynchronous; all expiry checks are enforced in queries regardless
of whether MongoDB has removed the record yet.

## Tests

`venv/bin/python -m pytest tests/test_auth_lifecycle.py tests/test_demo_chargers.py`
uses isolated `voltx_auth_test_*` databases on the configured Mongo server. Only
each test's freshly generated database is removed. It never uses DB_NAME for
fixtures. Tests require network access to that Mongo server.

The full integration suite also uses the local backend:
`REACT_APP_BACKEND_URL=http://localhost:8001 venv/bin/python -m pytest tests`.
It creates charging/repair/payment test records; prefer a disposable demo DB.
The adapters use real OTP requests and cookie sessions and honor rate limits.
No auth bypass is present. Existing demo balances/activity are never copied to new
customers.

## Google OIDC (optional second customer login)

Set `GOOGLE_CLIENT_ID` (public web client identifier), `GOOGLE_CLIENT_SECRET`
(secret, stored only in Render's secret environment), and `GOOGLE_REDIRECT_URI`.
For the production web client use client ID
`534491246723-56tblqjhhtp3iks4c27dv0pondaiish6.apps.googleusercontent.com`
and exact redirect URI `https://evchargerrepair.in/api/auth/google/callback`.
The redirect origin must be in `CORS_ORIGINS`. No infrastructure changes are
included. Missing configuration fails closed while SMS remains available.

Google requests only `openid email profile`. The callback always returns to
`/login`; the fresh page reloads `/api/auth/me` and follows existing dashboard
routing. No browser-supplied return URL is accepted. Google subjects are separate
customer identities; matching email never links accounts. Transactions expire
in five minutes, are bound to an HttpOnly browser cookie and atomically consumed.
Sessions and logout are shared with SMS. Existing strict Origin checks protect
all mutating cookie endpoints (the signed WhatsApp webhook remains exempt).
The Google callback uses state plus browser binding for login CSRF protection.
Application access logging strips callback query strings. Configure any external
proxy/access logs to redact callback query strings before a production rollout.

### Review and rollout checklist (separate production approval required)

- Confirm green CI, review OAuth security and preserve SMS/WhatsApp settings.
- Back up users and audit phone/provider indexes in a staging copy first.
- Startup builds `auth_phone_partial_unique` for string phones before removing
  legacy full unique phone indexes, then adds the unique provider/subject index.
  It preserves all users and aborts on normalized phone collisions/index errors.
  Empty strings remain unique; absent/null phones may occur on multiple accounts.
  Requires MongoDB 5.0+ for coexisting index options during migration (Atlas 8 supported).
- Configure the three Google variables privately, verify exact Google Console
  redirect registration and HTTPS cookie behavior, then approve rollout separately.
- Smoke test new/existing Google customers, logout, SMS and repair authorization.
- Rollback: disable Google entry by removing its secret configuration or revert
  the application release. Preserve users, identities, sessions and partial phone
  index. Do not restore a full phone index after phone-less customers exist.
  Do not roll back to code that recreates that index without a reviewed migration.
