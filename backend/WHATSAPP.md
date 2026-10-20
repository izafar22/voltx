# RushX WhatsApp Cloud API

This integration is **off by default**. It uses Meta's official Cloud API and a
separate durable worker. It does not register, migrate or disconnect any number.
Initial verification must use Meta's **test phone number** and test recipients.
The existing WhatsApp Business mobile number remains untouched. Production
onboarding/coexistence is a separate, human-controlled decision.

## Configuration and startup

Install normal backend dependencies; `httpx` is already included. Copy the keys
from `whatsapp.env.example` into your ignored `backend/.env` or secret manager.
Never put tokens in frontend variables, source code, screenshots or CI logs.
The API and worker must share the same MongoDB database and configuration.

| Variable | Purpose |
| --- | --- |
| `WHATSAPP_ENABLED` | Defaults to `false`. Enables event creation and worker sends. |
| `WHATSAPP_MODE` | Defaults to `test`; `production` is an explicit operator decision. |
| `WHATSAPP_ACCESS_TOKEN` | Meta test access token initially; rotate outside source control. |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta **test** sender phone-number ID, not a mobile phone number. |
| `WHATSAPP_VERIFY_TOKEN` | Operator-generated random webhook verification token. |
| `META_APP_SECRET` | Meta app secret for raw-body HMAC-SHA256 verification. |
| `WHATSAPP_API_VERSION` | Supported version chosen in Meta dashboard, formatted `vNN.N`; no assumed default. |
| `WHATSAPP_TEST_RECIPIENTS` | Comma-separated E.164 allowlist; test mode refuses every other destination. |
| `RUSHX_DISPATCH_ADDRESS` | Actual service/dispatch address, supplied by the business. |
| `WHATSAPP_TEMPLATES_JSON` | Status-to-approved-template mapping, below. |

Start the existing API normally. From `backend/`, run the worker separately:

```sh
python -m services.whatsapp_worker
```

Use a process supervisor with restart-on-failure. No FastAPI background task or
in-process queue is needed. Multiple workers use Mongo atomic leases. The worker
creates indexes on job state/due time, message ID, embedded events and receipt
processing time. Grant its database account only the required collection access.
A standalone Mongo server is supported; replica-set transactions are not required.

## Consent and repair compatibility

`POST /api/repairs` accepts `whatsapp_opt_in: true|false`, default `false`, with a
strict boolean type. The checkbox starts unchecked. Opt-in stores timestamp,
`repair_submission_v1` source and the authenticated account's E.164 phone number.
Request-body recipient fields are never used. An invalid account number with
opt-in returns 422; ordinary repair submissions remain unaffected.

The worker rechecks the persisted consent and destination before each attempt.
If a customer asks to withdraw consent, authorized support must set that repair's
`whatsapp_consent.opted_in` to `false`; there is no new customer preference screen
in this scoped integration. Pending work will then dead-letter without sending.
Do not edit a destination to an arbitrary number; obtain fresh consent instead.
Consent and outbox internals are omitted from repair API responses, including
owner views of another customer's repair. Existing routes, authorization,
diagnosis filtering, status strings and transition graph remain intact.

Only events occurring while the feature flag is enabled are enqueued. Enabling
later does **not** retroactively message older repairs. Disabling the API flag
stops new events; restart/stop all workers with the flag disabled to stop pending
sends. A request already in flight cannot be recalled.

## Approved Utility templates

No template is assumed to exist. Create Utility templates in the Meta dashboard,
obtain approval, then configure their exact names and language codes. Example
mapping shape (names below are **proposals**, not existing approved templates):

```json
{
  "REQUESTED": {"name": "rushx_repair_confirmation", "language": "en", "parameters": ["repair_number", "dispatch_address"]},
  "RECEIVED_AT_VOLTX": {"name": "rushx_repair_received", "language": "en", "parameters": ["repair_number"]},
  "DIAGNOSING": {"name": "rushx_repair_diagnosing", "language": "en", "parameters": ["repair_number"]},
  "ESTIMATE_SENT": {"name": "rushx_estimate_ready", "language": "en", "parameters": ["repair_number"]},
  "REPAIR_COMPLETED": {"name": "rushx_repair_completed", "language": "en", "parameters": ["repair_number"]},
  "SHIPPED_TO_CUSTOMER": {"name": "rushx_repair_shipped", "language": "en", "parameters": ["repair_number"]}
}
```

Set this as a single JSON environment value. `parameters` is the **positional
body parameter order** in the approved template. Allowed keys are `repair_number`,
`dispatch_address`, `status_text`; no headers/buttons/named parameters are generated.
Confirmation requires the actual repair number and address; other repair templates
require the repair number. `status_text` is optional and uses the fixed RushX
wording in `STATUS_TEXT`. Empty required values fail closed. Proposed body wording:

| Event | Example template body |
| --- | --- |
| REQUESTED | RushX has received repair request {{1}}. Send your charger to {{2}} and include your repair number. |
| RECEIVED_AT_VOLTX | RushX has received your charger for repair request {{1}}. |
| DIAGNOSING | RushX is diagnosing your charger for repair request {{1}}. |
| ESTIMATE_SENT | Your RushX estimate for repair request {{1}} is ready. Review it in the app. |
| REPAIR_COMPLETED | RushX has completed the repair for request {{1}}. Check the app for next steps. |
| SHIPPED_TO_CUSTOMER | RushX has marked the charger for request {{1}} as shipped. Check the app for shipment details. |

Do not claim a delivery date, payment status, warranty, shipping carrier or tracking
number that the app has not verified. No internal notes or diagnosis fields enter
payloads. Internal `IN_TRANSIT_TO_VOLTX` / `RECEIVED_AT_VOLTX` identifiers are
preserved; customer template text says **RushX**. Other intermediate/customer-set
statuses intentionally produce no WhatsApp message.

For an initial Meta test-number smoke test only, the supplied sandbox template can
be mapped to `REQUESTED` as
`{"REQUESTED":{"name":"hello_world","language":"en_US","parameters":[]}}`
if it is available in that test account. This exception works only in `test` mode;
it verifies transport but **does not verify the RushX confirmation content**.
Full acceptance testing requires the approved RushX templates above.

## Durable delivery and recovery

Repair creation atomically inserts its consent and notification event into the
same Mongo repair document. Status updates atomically append a UUID event and
change status using a compare-and-set on the previous status. A racing request
gets 409, and a repeated/invalid transition cannot create an event. Creation keys
are `repair_id:REQUESTED`; subsequent keys are `repair_id:status_history_event_id`.

The worker upserts each embedded event into `whatsapp_jobs` using its unique Mongo
`_id`, then removes that event from the repair. A crash before or after either
operation leaves an event to reconcile or an existing durable job. Delivery does
not affect repair HTTP responses. No separate enqueue write is required in the
request handler. The event snapshots the actual repair number and configured
address; if the business changes the address, already queued jobs retain their
original instructions and require operator review.

Jobs progress through `pending`, `processing` (120-second lease), `sent` (Meta HTTP
acceptance only), then `delivered` / `read` / `failed` via webhooks. Retryable HTTP
429/5xx, known Meta throttling codes and transport failures enter
`retryable_failure` with exponential delays of 30/60/120/240 seconds. Retry-After
seconds or HTTP dates are honored up to one day. Five attempts, including recovered
leases, are allowed. Permanent API/configuration errors and exhausted attempts
enter `dead_letter`. Malformed successful responses also dead-letter for manual
review. HTTP requests have a 20-second timeout and redirects are disabled.

**Exactly-once provider delivery is not guaranteed.** Unique event keys prevent
ordinary duplicate scheduling; fenced leases prevent concurrent normal sends.
If Meta accepted a message but acknowledgement persistence failed, or a request
timed out after acceptance, retrying can send it again. A long process pause past
its lease has the same risk. `biz_opaque_callback_data` correlates early webhooks
with jobs and can prevent a replay after a crash, but is not a Meta idempotency
key. Different events may arrive out of order after retries.

The webhook stores a minimal durable receipt before acknowledging. The worker
applies monotonic ranks (`sent < failed < delivered < read`) so duplicate and late
callbacks cannot regress delivery state. Delivery/read evidence wins over failure.
Unknown message IDs are retained and checked again after 60 seconds; they do not
block matched receipts. Webhook `failed` is terminal and requires operator review;
it does not blindly resend an accepted message.

To recover configuration failures, first stop the worker, fix configuration, then
inspect the exact dead-letter job and consent in restricted database tooling.
For an **unsent configuration failure only**, correct any missing snapshotted
address after business review, and set that specific job to `pending`, `attempts`
to `0`, and `next_attempt_at` to the current BSON UTC date. Keep its `_id`.
Never bulk-delete jobs or replay sent/delivered/read/ambiguous jobs automatically.
Check Meta delivery evidence before manually retrying uncertain outcomes.

## Webhook and manual test-number setup

1. Create/configure a Meta developer app with the WhatsApp product. Use its test
   WABA and test phone-number ID. Add only consenting test recipients in Meta.
   Do not register or migrate the existing Business App number.
2. Configure test credentials, test recipient allowlist, actual dispatch address,
   version and approved templates. Leave the flag off until ready.
3. Expose the API callback over HTTPS at `/api/webhooks/whatsapp`. Configure its
   verify token in Meta and subscribe to the `messages` webhook field.
4. GET verification requires `hub.mode=subscribe` and the configured token and
   returns the exact `hub.challenge` as plain text. POST requires HMAC-SHA256 over
   the original request bytes in `X-Hub-Signature-256`. The exact callback route
   bypasses browser Origin validation; other mutating routes still require it.
   Inbound messages are ignored; automated two-way replies are not enabled.
5. **Redact query strings on this callback in proxy/APM logs** (the GET verify
   token is a query parameter). The integration strips this callback query from
   uvicorn access records. For other servers, disable access logs if query
   redaction is unavailable. Never enable HTTP wire/header/body debug logs.
6. Enable in the test environment, restart API/worker, submit an explicitly
   opted-in repair, and confirm one job, the correct repair number/address and
   the recipient's actual received message. Submit without opt-in: no job/message.
7. Exercise receipt, diagnosis, estimate, completion and shipping transitions;
   verify RushX wording, status history, stored message ID and delivered/read
   callbacks. A successful HTTP response alone is not proof of delivery.
8. Try duplicate/invalid transitions and invalid signatures, restart the worker
   with an unfinished lease, and confirm recovery. Use mocks for provider error
   scenarios; do not deliberately spam Meta. Keep production disabled until this
   human verification and template approvals are complete.

Official references: [Meta webhook verification](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/),
[Meta Cloud API collection](https://www.postman.com/meta/whatsapp-business-platform/overview),
[Meta WhatsApp documentation](https://developers.facebook.com/documentation/business-messaging/whatsapp/overview).
Consult the current app dashboard for supported API versions and permissions.

## Operations and tests

Monitor `whatsapp_jobs` counts grouped by `state` and `error_code`, oldest pending
`created_at`, oldest due `next_attempt_at`, expired `processing.lease_until`, number
of outstanding repair outbox events, and unprocessed `whatsapp_receipts`. Alert on
worker cycle errors, any dead-letter growth, old sent jobs without callbacks and
queue lag. Query metadata in restricted tooling; do not export destinations,
consent data, tokens or template contents into general logs. Apply your approved
retention policy to completed jobs/receipts, but retain idempotency records while
source events may be replayed. No automatic TTL deletes are introduced.

```sh
# From backend/ (activate your virtual environment first):
pip install -r requirements-test.txt
python -m pytest tests/test_whatsapp.py -q
# Existing auth/demo tests use a disposable database on configured MONGO_URL:
python -m pytest tests/test_auth_lifecycle.py tests/test_demo_chargers.py tests/test_whatsapp_mongo.py -q
# Existing live repair/API tests need a separately seeded, disposable test API:
REACT_APP_BACKEND_URL=http://127.0.0.1:8001 python -m pytest tests/test_repairs.py tests/test_phase2_repair_flow.py tests/backend_test.py -q
# From frontend/:
CI=true npm test -- --watchAll=false --runInBand
npm run build
```

Run live suites only against a disposable database with `APP_ENV=test`,
`OTP_MODE=demo`, `EXPOSE_DEMO_OTP=true`, `WHATSAPP_ENABLED=false`. All new provider
calls use `httpx.MockTransport`; no real messages are sent in automated tests.
