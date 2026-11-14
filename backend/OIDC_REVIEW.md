# PR #10 pre-merge review

## Changes and verification

Customer-visible login/repair copy, the shared logo name, and the page title now
use RushX. Stored repair status keys (`IN_TRANSIT_TO_VOLTX`,
`RECEIVED_AT_VOLTX`), charger IDs and historical repair numbers stay unchanged.

The migration tests run on a disposable, local MongoDB 8.0.16 database, never on
production. They cover both legacy index names (`phone_1`, `auth_phone_unique`),
existing customer/owner/admin roles, a formatted valid phone, a malformed historical
phone and a historical phone-less user. They verify normalization, preserved user
IDs/roles, wallet balances and repair history, successful existing SMS login,
multiple missing/null phone records, duplicate phone/Google identity rejection,
no email-based merge, and repeated startup. A normalization collision leaves both
records and the legacy index untouched. No production MongoDB audit or migration
was performed.

The callback retains single-use browser-bound state, PKCE, nonce and validated
Google signature/issuer/audience/expiry. Redirect destinations remain fixed.
A redundant transaction-cookie header was removed: callback responses now expire
the transaction cookie once, instead of both setting an empty cookie and deleting
it. HTTPS tests cover host-only Secure/HttpOnly/SameSite=Lax session cookies at
`/`, transaction cookies at `/api/auth/google`, session replacement/revocation,
logout, no-store/no-referrer responses, and refusal to send Secure cookies on HTTP.
Google HTTP/JWKS are mocked; no real Google authorization was initiated.

## Same-origin routing review

Frontend Axios uses `/api` with credentials and Google sign-in uses top-level
navigation to `/api/auth/google/login`. Production must keep the browser on
`https://evchargerrepair.in` throughout API and callback handling. Per
[Render's routing documentation](https://render.com/docs/redirects-rewrites),
the first matching rule wins and a rewrite preserves the browser URL.

Authenticated read-only inspection in imran's workspace confirmed these exact
rules on frontend service `srv-daaa1aoae00c73a70g70`, in this order:

1. `/api/*` → `https://voltx-backend-lp42.onrender.com/api/*`, action **Rewrite**.
2. `/*` → `/index.html`, action **Rewrite**.

The Headers page has no custom response-header rules. No rules were edited or
saved. These rules preserve the API path and put the API before SPA fallback. Preserve the `/api` prefix, callback query string,
Origin and Cookie request headers, Set-Cookie and Location response headers,
status codes and methods. Auth responses must not be cached. Callback query
strings must be redacted from proxy/access logs.

A read-only public GET of `https://evchargerrepair.in/api/auth/me` returned
HTTP 401 JSON (`Not authenticated`), `Cache-Control: no-store` and
`x-render-origin-server: uvicorn`, without redirecting to another origin. This
confirms that the deployed same-origin API path reaches FastAPI. One earlier
request timed out; the retry succeeded. It does not prove callback query/cookie
forwarding for this undeployed feature. Dashboard rule inspection is complete;
no production settings were changed. Both frontend and backend services track
`repair-mvp` with automatic deployment on commits, and PR previews are off.
A merge into `repair-mvp` is therefore also a production deployment trigger,
not a review-only step. No merge or deployment was performed.

## Deployment gates

- Review green CI and approve rollout separately. This PR remains a draft.
- The exact Render rewrite order/destination is confirmed. Verify query/header
  forwarding, cache bypass and proxy log redaction in a staging OAuth round trip
  before production. PR previews are currently off; this review did not create
  or enable any staging infrastructure.
- Account for automatic deployment of both services on `repair-mvp` commits:
  separate rollout approval must precede a merge. No auto-deploy setting was changed.
- Privately configure/verify GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and
  GOOGLE_REDIRECT_URI=https://evchargerrepair.in/api/auth/google/callback,
  matching Google Console registration and HTTPS CORS_ORIGINS. No secret values
  were inspected or committed by this review.
- Audit production phone/provider identities, confirm MongoDB 5+ and index
  permissions, back up data, and stop old writers for the migration window.
  This review used representative fixtures, not a production data copy.
- SMS provider integration remains unconfigured in this repository. Preserve its
  fail-closed 503 behavior; real SMS delivery requires a configured provider.
- Preserve WhatsApp/payment enablement settings. Rollback must preserve the partial
  phone index and phone-less users; see AUTH.md for the rollback checklist.
