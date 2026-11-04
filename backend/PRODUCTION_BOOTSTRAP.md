# Prelaunch production bootstrap and Google administrator enrollment (v1)

This is an operator runbook for issue #24, not permission to merge or deploy. The implementation was tested only against disposable loopback MongoDB. No Render settings or production/staging databases were changed. The issue describes `rushx_production` as pre-created and empty; recheck that assumption privately before launch. Do not run the full test suite against Atlas: existing tests create/drop fixture databases and exercise demo APIs.

## Design and invariants

`python -m backend.production_cli` is independent of `server.py`: it never loads `.env`, imports the application, seeds demo identities/chargers, or drops indexes. Bootstrap version 1 is defined by `services/index_contract.py`, shared with the existing safety/auth startup initializers. It inspects ordered keys, uniqueness, sparse settings, partial expressions, TTL seconds, hidden state and collation, accepting an equivalent index under another name. Same-key/name conflicts fail closed, without an automatic drop or option rewrite. Missing indexes are built by those startup initializers and verified afterwards. All required indexes are checked before creating any; a failed build can leave some new indexes installed, so fix the underlying issue privately and rerun, rather than deleting indexes blindly. Bootstrap is repeatable and creates zero documents. It does not normalize existing phone records; legacy normalization or index conflicts require a separate reviewed migration. Startup's existing legacy-phone migration is retained for compatibility; the CLI disables it.

The v1 contract includes payment idempotency uniqueness, sparse unique repair creation keys, the four repair pagination indexes, partial unique phone and Google provider/subject identities, unique user and wallet identifiers, five zero-second expiry TTL indexes, and the OTP phone lookup. Ordinary pre-created query indexes are reused. Verification does not treat a matching name alone as correctness. MongoDB documents [index option behavior](https://www.mongodb.com/docs/manual/reference/method/db.collection.createindexes/) and [partial uniqueness](https://www.mongodb.com/docs/manual/core/index-partial/); this tool deliberately stops instead of trying to repair conflicts automatically.

Google login uses the verified token's immutable `sub` and never grants privilege by email/domain. [Google recommends `sub` rather than email as the account identifier](https://developers.google.com/identity/openid-connect/openid-connect). New identities still insert as customers; existing active customer/owner/admin roles are preserved. Admin/owner callbacks additionally require an explicitly active stored account and a verified Google email. State, nonce, PKCE, issuer, audience, signing-key checks, transaction consumption, same-origin redirects and Secure/HttpOnly/SameSite cookies remain in place. Backend authorization reads the stored role on every request; the JWT role is not an authorization source.

There is no self-service enrollment/promotion API. The one-time operator CLI only promotes a **Google-only customer identity already enrolled by a valid callback**, with verified email evidence recorded by the server within 24 hours. It requires the exact Google subject, matching verified email, explicit `--promote-existing-customer`, an active record and no conflicting account using that email. Phone-linked, inactive, owner, ambiguous, unverified, stale or missing identities are rejected. It never merges identities. Concurrent attempts use a conditional update; exact retries are idempotent. A new auth epoch atomically invalidates all earlier sessions when promotion occurs, and existing sessions are then deleted. The administrator must sign in again. Name/email/subject input is hidden in an interactive terminal, never passed as shell arguments or printed. Keep database access and the operator terminal restricted; database write access can already grant roles.

## Local validation (never use production credentials)

Install the existing Python requirements and start a disposable MongoDB 8 instance bound to loopback, e.g. port 27027 with a fresh temporary data directory. Use a new test-only DB and test-only secret. Existing integration tests require a disposable API in demo mode, exclusively in `APP_ENV=test`:

```sh
export MONGO_URL='mongodb://127.0.0.1:27027'
export DB_NAME='rushx_bootstrap_test_api'
export JWT_SECRET='local-test-only-secret-at-least-32-characters'
export APP_ENV='test'
export OTP_MODE='demo'
export EXPOSE_DEMO_OTP='true'
export CORS_ORIGINS='http://localhost:3000'
export WHATSAPP_ENABLED='false'
# In a separate terminal with the same test-only environment:
(cd backend && python -m uvicorn server:app --host 127.0.0.1 --port 8024)
# Wait for GET http://127.0.0.1:8024/api/ to succeed, then:
(cd backend && REACT_APP_BACKEND_URL=http://127.0.0.1:8024 python -m pytest)
(cd frontend && CI=true corepack yarn test --watchAll=false --runInBand)
(cd frontend && corepack yarn build)
```

The new real-Mongo test explicitly rejects non-loopback targets and uses a random disposable database, separate from DB_NAME. Other pre-existing tests also use disposable databases but rely on the supplied MONGO_URL; do not substitute an Atlas URI. Google HTTP/JWKS traffic is mocked. Keep `backend/pytest.ini` worker settings unchanged.

## Manual launch sequence — requires your approval and execution

1. Review/merge the PR only when ready, then select the exact tested commit. Take an appropriate Atlas backup/snapshot and record the current Render commit, `DB_NAME=voltx_staging`, existing secret references and rollback configuration privately. Confirm prelaunch/no customer traffic and no workers writing to the new target. Do not copy demo/staging records into production.
2. Use Atlas credentials scoped only to `rushx_production`, with the required find/listIndexes/createIndex and user/session write permissions. Prefer a short-lived migration/operator identity with createIndex and a separate runtime identity with only the app's necessary privileges. Runtime startup still initializes indexes, so either grant its needed createIndex privilege or ensure the deployment's established operational policy supports that initialization. Do not grant dropDatabase, broad all-database access or staging write access merely to run this tool. Restrict network allowlisting and keep URI/credentials in a secret manager. If the URI includes a default database path it must match the target (a separate authSource query parameter is fine).
3. In a trusted private terminal, supply the following environment from the secret manager. Do not paste values into chat, commit them, enable shell tracing, export them in CI artifacts, or put secrets on command lines. The CLI does **not** load `.env`:

| Variable | Required operator value |
| --- | --- |
| MONGO_URL | Secret Atlas URI scoped to the target; optional URI database path must match DB_NAME |
| DB_NAME | `rushx_production` |
| APP_ENV | `production` |
| OTP_MODE | `provider` (never demo) |
| EXPOSE_DEMO_OTP | `false` |
| JWT_SECRET | Existing strong stable secret, at least 32 characters; do not rotate incidentally |
| CORS_ORIGINS | Explicit HTTPS frontend origins, e.g. `https://evchargerrepair.in`; no wildcard |

4. From repository root, first inspect without writes, then explicitly apply the v1 bootstrap:

```sh
python -m backend.production_cli bootstrap --database rushx_production
python -m backend.production_cli bootstrap --database rushx_production \
  --apply --confirm-database rushx_production
python -m backend.production_cli bootstrap --database rushx_production
```

The final output must be `Bootstrap v1: missing_indexes=0`. The first read-only command may report missing indexes before applying. Invalid/missing settings, URI/DB_NAME mismatch and insecure production auth settings fail closed. For independent zero-seed confirmation, privately count documents in all pre-created collections before and after; all must remain zero at this point. Do not proceed on duplicate/index conflicts. This runbook supplies commands but they have **not** been run against Atlas.

5. Manually change the Render backend's `DB_NAME` from `voltx_staging` to `rushx_production` (and its database credential reference if using the recommended per-DB credential). Verify `APP_ENV=production`, `OTP_MODE=provider`, `EXPOSE_DEMO_OTP=false`, stable JWT_SECRET, explicit HTTPS CORS_ORIGINS, and the configured SMS provider. Independently verify Google client ID/secret and exact authorized redirect URI `https://evchargerrepair.in/api/auth/google/callback`. Preserve the same-origin API rewrite and cookie headers. Deploy/restart the reviewed backend commit **only after approval**; review sanitized startup logs. Do not enable demo mode to bypass missing SMS configuration. These are manual steps; this PR does not alter Render or production configuration.
6. Enroll the intended administrator by signing in with their Google account through the normal production login once. Initially they are a customer and must be denied admin APIs. The Google callback verifies the ID token signature, issuer, audience, expiry and nonce and writes `google_verified_email`/`google_verified_at`; no browser-supplied subject or profile email is accepted as proof. In the authenticated browser, use `/api/auth/me` to identify that specific account's `user_id`. A trusted database operator privately looks up **that user_id**, then checks `auth_provider=google`, `auth_subject`, the matching verified email, active status and fresh verification time. Share neither tokens nor identity records in screenshots/chat/logs. Do not choose a record merely by matching email, decode an unverified JWT, use a copied arbitrary subject, or promote an old demo admin record. If the account was enrolled before this version, perform a fresh Google login to obtain server-written evidence.
7. Run the operator promotion in an interactive trusted terminal using the same explicit target environment:

```sh
python -m backend.production_cli provision-admin --database rushx_production \
  --apply --confirm-database rushx_production --promote-existing-customer
```

Enter the operator-verified Google subject, verified email and administrator display name at the hidden prompts. No values appear in shell history/process arguments. Output is only `provisioned` or `unchanged`. A missing/stale/conflicting record is an error requiring review, not permission to edit arbitrary accounts or drop uniqueness. If an earlier customer session exists it becomes invalid at promotion; sign out and sign in again. Repeat the identical command to check idempotency if necessary; do not use it to rename or relink an administrator.
8. Perform the smoke tests below. Until successful, launch remains blocked. The CLI intentionally requires one verified first-login enrollment, so an empty DB cannot have an admin before these operator-mediated steps. Keep this restricted prelaunch window controlled.

## Manual smoke checks

- Logged out: `/api/auth/me` and `/api/admin/summary` return 401; `/admin` redirects to login. Confirm no session/token/PII in URLs or logs.
- Intended Google admin, after re-login: `/api/auth/me` returns `role=admin`; `/admin` renders the admin screen; read-only `/api/admin/summary` succeeds. Verify host-only Secure, HttpOnly, SameSite=Lax `access_token` cookie at `/`, transaction-cookie deletion, callback no-store/no-referrer headers, and session rotation/logout. Do not perform financial, charger-control or repair mutations as a smoke test.
- Separate normal Google user: remains customer, reaches customer home, `/admin` redirects to their role home and `/api/admin/summary` returns 403. An email/domain resemblance must not change that result.
- Existing pre-provisioned owner (if one is deliberately created through a separately authorized process): verified active Google identity remains owner and is denied admin APIs. This CLI provisions only admins; it does not link phone owners by email.
- Phone OTP: with real configured delivery, existing phone login/customer registration still works. Never use demo OTP in production; if SMS delivery is unconfigured, report the blocker rather than claim SMS readiness.
- Confirm customer signup/onboarding, repair request/tracking navigation and WhatsApp configuration remain as intended, using a separately authorized test plan for any actual data writes. No live delivery or repair write was performed by this implementation.

## Rollback and recovery

Before traffic, if initialization/enrollment/login smoke checks fail, stop the launch. Manually restore Render DB_NAME to `voltx_staging`, restore its scoped credential reference if changed, and restart/redeploy the recorded previous backend commit/configuration. Restore **all** production auth safeguards; never turn on demo mode. Cookies from the new database have no matching sessions in staging, so require re-login. Confirm `/api/auth/me`/role authorization again. Do not copy new database sessions/accounts into staging or delete the new database/indexes as rollback.

If any real traffic/writes have occurred, pause and reconcile changes before switching DBs; reverting the pointer alone would hide new records. Retain backups and both databases for a separately reviewed recovery. For a mistaken admin promotion, a trusted operator must explicitly revoke/demote the exact subject-bound account and invalidate its sessions/auth epoch under a separately approved incident procedure; do not reassign its subject or merge it with another account. Removing the CLI or rolling back code does not undo a stored role. No production demotion, deletion, index drop or rollback was executed here.

## Remaining manual actions / evidence limits

You must approve release, supply scoped credentials, inspect Atlas counts/conflicts, run bootstrap, configure/switch Render and restart, enroll/verify/promote the intended Google identity, and perform live same-origin/admin/customer/SMS smoke tests. We have not independently audited the issue's production state in this task. Unit/integration tests establish behavior on disposable local MongoDB and mocked Google, not Google Console, Atlas, Render rewrite or real SMS readiness. Review any index-build failure privately without publishing driver errors containing documents or URIs.

### Validation recorded for this PR

- Full backend suite: **304 passed, 3 skipped** on disposable loopback MongoDB 8.0.16 and a test-only API. The existing skips concern absent session/withdrawal/owner-wallet fixture data. Existing dependency/deprecation warnings remain.
- Frontend: **168 passed across 16 suites**, including signed-out/customer/owner denial of the admin route and direct admin access; production build passed.
- Actual v1 CLI apply was run twice on a fresh loopback-only database, then checked without `--apply`; all three runs reported `missing_indexes=0`. Integration tests independently assert zero records after bootstrap, semantic index equivalence/no duplicate builds, unique constraints and conflict rejection without drops.
- Google tests use mocked provider responses and locally signed test tokens, covering verified admin/owner callbacks, customer defaults, email non-linking, invalid roles/inactive accounts/unverified privileged email, state/binding/nonce/signature/audience/expiry failures, replay/concurrency, session roles and backend authorization. Earlier sessions are invalidated on operator promotion.

Use a fresh disposable API database for each complete test-suite run. Reusing its rate-limit collections immediately can correctly trigger OTP throttling; do not weaken rate limits to make a repeated suite pass. No production, staging, Render or real Google/SMS operation was performed for these results.
