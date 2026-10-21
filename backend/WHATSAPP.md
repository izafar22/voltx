# RushX WhatsApp repair notifications

Issue #3 extends PR #2's embedded outbox, worker and signed webhook; it is not a
second messaging implementation. Release target: **repair-mvp**. The integration
is **off by default**. Production activation, template submission/approval, number
onboarding and live sends are separate human-controlled actions. Do not register,
migrate, disconnect or change the existing WhatsApp Business App number.

See [manual payment architecture and setup](PAYMENTS.md) for receipt verification,
optional reviewed merchant QR, recovery/rollback and the separate ninth event.

## Eight lifecycle events and authoritative facts

| Stored status | Proposed Utility template | Snapshot body parameters, in order |
| --- | --- | --- |
| REQUESTED | rushx_repair_requested_v1 | customer_name, repair_number, charger_description |
| AWAITING_SHIPMENT | rushx_awaiting_shipment_v1 | customer_name, repair_number, dispatch_address |
| RECEIVED_AT_VOLTX | rushx_charger_received_v1 | customer_name, repair_number |
| ESTIMATE_SENT | rushx_estimate_ready_v1 | customer_name, repair_number, estimate_total |
| CUSTOMER_APPROVED | rushx_estimate_approved_v1 | customer_name, repair_number |
| REPAIR_COMPLETED | rushx_repair_completed_v1 | customer_name, repair_number |
| PAYMENT_PENDING | rushx_payment_pending_v1 | customer_name, repair_number, amount_due |
| SHIPPED_TO_CUSTOMER | rushx_return_shipped_v1 | customer_name, repair_number, courier, tracking_number |

All templates use **en_US** and positional BODY text parameters. Exact copy,
fictional sample values and per-template verification checklists are in
[the JSON catalog](templates/whatsapp_utility_catalog.json) and
[the Meta submission guide](templates/WHATSAPP_SUBMISSION.md). Proposed copy from
Issue #3 is unchanged. Actual approval and classification are not guaranteed.
Do not edit templates already in review. Nothing is submitted by this code.

Only these eight repair statuses enqueue lifecycle events. A separately verified
full receipt emits the ninth `PAYMENT_RECEIVED` event without changing repair status. In particular, `DIAGNOSING` no longer
sends. `IN_TRANSIT_TO_VOLTX` and `RECEIVED_AT_VOLTX` remain internal identifiers;
customer labels use RushX. Do not introduce ESTIMATE_APPROVED or RETURN_SHIPPED.
The existing graph, including declined/not-repairable/cancelled paths, is retained.

The customer name comes from the authenticated account on creation and from the
repair submitter's account on later transitions, never from the admin changing
status. Recipients come only from recorded authenticated-account E.164 consent.
Each event contains only the fields its template requires. No diagnosis, staff
notes, payment reconciliation references, customer address or invented URL enters
a message. Missing personalization/address leads to an unsent `snapshot_invalid`
job; no placeholder greeting or fabricated business facts are sent.

### Documented API validation changes

These business checks apply even when WhatsApp is disabled or the customer did
not opt in, so the app cannot publish misleading repair facts:

- `ESTIMATE_SENT` requires a persisted estimate whose finite, non-negative INR
  total matches its parts, quantities, fees and tax. Draft saves do not send.
  The transition atomically marks it SENT and records publication time. Published
  estimates are immutable: later edits return 409. The admin editor shows them
  as locked. A revised-quote workflow is a separate future change.
- `CUSTOMER_APPROVED` and `CUSTOMER_DECLINED` require a valid published estimate.
  Legacy estimates marked SENT with consistent persisted line items/totals remain
  usable. Estimates missing those facts require support review, never fabrication.
- After REPAIR_COMPLETED, an admin records the reconciled balance using
  `PATCH /api/repairs/{id}/payment` with `amount_due` and an internal `reference`.
  The admin UI supplies this form. This is a manual attestation **after accounting
  for all confirmed payments**. This endpoint does not collect money or record a
  receipt; the separate receipt-verification API is documented in PAYMENTS.md. Currency is INR; verified actor/time/source are server-set.
  Saving does not notify. PAYMENT_PENDING requires a positive verified amount.
  A subsequent balance change cancels an unsent notice rather than sending a
  stale amount. Customer responses show only amount/currency/verification time.
- Zero-due repairs cannot enter PAYMENT_PENDING. The existing graph has no direct
  REPAIR_COMPLETED → READY_TO_SHIP edge; a future zero-balance workflow needs an
  explicit business decision. Do not invent a charge to bypass this guard.
- Return shipment metadata is now **admin-only**, to prevent customers from
  declaring their own return dispatch. An admin saves real courier/tracking data
  through the existing shipment endpoint. Confirmed actor/time are recorded and
  hidden from customer responses. Partial drafts are allowed but cannot dispatch.
  SHIPPED_TO_CUSTOMER requires both fields and confirmation. Metadata saves do not
  send. Dispatched courier/tracking fields are locked; administrative corrections
  need support review rather than a second automatic notification.
- AWAITING_SHIPMENT remains customer-settable, as the existing submission UI
  advances REQUESTED to AWAITING_SHIPMENT. It means instructions for the customer's
  inbound dispatch, **not** a claim of carrier collection. This permission is not
  silently transferred to admins. Incoming shipment metadata permissions remain.

Relevant writers use an optimistic `revision` guard; legacy absent revisions are
supported. If estimate, balance, shipment, consent or status changes after a
request reads it, that request receives 409 and must refresh. Status history and
its notification event share one atomic repair-document write. Diagnosis edits
and outbox reconciliation do not change business revision.

## Configuration and production gates

Use [whatsapp.env.example](whatsapp.env.example) as a non-secret starting point.
Store credentials in ignored environment files or a secret manager, never browser
variables, sample files, PRs, logs or screenshots. API and worker share configuration
and MongoDB database. Separate test and production databases/apps/credentials.

| Variable | Meaning |
| --- | --- |
| WHATSAPP_ENABLED | Defaults false; controls new events and worker sending. |
| WHATSAPP_MODE | Defaults test; production must be selected explicitly. |
| WHATSAPP_ACCESS_TOKEN | Scoped Meta access token, initially the test environment token. |
| WHATSAPP_PHONE_NUMBER_ID | Selected sender ID, not a mobile number. |
| WHATSAPP_TEST_PHONE_NUMBER_ID | Independently configured Meta test sender ID; must equal the selected sender in test mode and differ in production. |
| WHATSAPP_TEST_RECIPIENTS | Explicit allowlist of consenting Meta test recipients in E.164. |
| WHATSAPP_VERIFY_TOKEN | Random operator-provisioned GET verification token. |
| META_APP_SECRET | HMAC key for POST webhook authentication. |
| WHATSAPP_API_VERSION | Currently supported Graph version chosen in the Meta dashboard. No assumed default. |
| RUSHX_DISPATCH_ADDRESS | Actual approved RushX facility address, as a single line. |
| WHATSAPP_TEMPLATES_JSON | Exact template names, en_US, ordered parameter keys, category and verified approval status. |
| WHATSAPP_PRODUCTION_APPROVED | Defaults false; additional manual rollout gate, not a claim that approval exists. |

A mapping entry looks like:

```json
{"REQUESTED":{"name":"rushx_repair_requested_v1","language":"en_US","category":"UTILITY","approval_status":"unknown","parameters":["customer_name","repair_number","charger_description"]}}
```

Replace `unknown` with `approved` only after a human confirms the exact template,
locale, category, body and parameter order in the correct Meta account. This is
local verification metadata; Meta is still authoritative and can reject sends or
change approval/classification. Unknown/rejected/pending, missing or malformed
entries fail closed. Production requires **all eight** approved entries, a sender
different from the configured test sender, explicit production mode and the extra
manual gate. Correct business facts cannot bypass bad configuration.

For test transport only, a selected event may map to
`{"name":"hello_world","language":"en_US","parameters":[]}` if available in
that Meta test account. All business snapshot validation and recipient/sender
isolation still apply. `hello_world` is always forbidden in production. It cannot
verify actual RushX content, variable order or template approval.

Start the worker separately from `backend/`:

```sh
python -m services.whatsapp_worker
```

Use a process supervisor. No provider HTTP happens in FastAPI repair handlers.
The worker uses async httpx with redirects disabled and a 20-second timeout.
It builds queue, lease, receipt and observability indexes. API permissions need
repair/user reads/writes and receipt upserts; the worker needs queue/reconciliation
access. Use separate restricted credentials per environment and role. Only people
performing template administration need the corresponding Meta management access.

## Delivery, idempotency and safe recovery

Creation keys are `repair_id:REQUESTED`; transition keys use the status-history
event ID. The outbox is embedded in the same repair document as the mutation.
Reconciliation upserts a job by its unique `_id` and then removes the embedded
event. A crash between these writes is recoverable on standalone MongoDB/Atlas;
no distributed transaction is required. Snapshots are immutable and versioned.
They include mode and sender binding: test jobs cannot be drained into production.

States: `pending` → `processing` (120-second lease) → `sent` (Meta acceptance only)
→ `delivered` / `read` / `failed` from signed receipts. Processing claims are atomic
and fenced. Persisted send intent precedes the HTTP request. A process crash after
that marker, read/write timeout, protocol failure or malformed successful response
is **ambiguous** and dead-letters without automatic replay. Connect/pool failures
before dispatch can retry. A stale worker cannot start sending with a replaced
lease. A stop or consent withdrawal cannot recall an HTTP request already started.

Explicit 429, known throttle codes and 5xx responses retry with exponential delay
(30/60/120/240 seconds; five total claims max). Retry-After seconds/HTTP dates are
honored up to one day. A shared per-sender pause prevents other jobs/workers from
hammering a throttled sender. Exhausted attempts and permanent/configuration errors
dead-letter. No raw provider error body or exception text is persisted or logged.

There is no claim of provider-level exactly-once delivery: Meta offers no local
transaction with MongoDB. This implementation prioritizes avoiding duplicate
messages when delivery is uncertain, so an ambiguous job may need human
reconciliation even if it never reached Meta. Explicit provider error retries can
still inherit provider-side uncertainty. Events can arrive out of order after
retries. Accepted/delivered/read jobs are never automatically requeued.

Webhooks are acknowledged only after minimal durable receipts are written. Each
receipt has a deterministic deduplication key. Sender scope and opaque event IDs
correlate early callbacks; late callbacks cannot downgrade read/delivered states.
Ranks are sent < failed < delivered < read. Unknown IDs are deferred 60 seconds
without blocking other receipts. A failed delivery is not automatically resent.

### Safe single-job replay

1. Stop or pause the relevant worker; inspect one job in restricted DB tooling.
   Review Meta evidence and the current customer consent. Do not print payloads.
2. Fix only configuration or infrastructure issues. Do not invent missing facts,
   mutate snapshots, delete idempotency keys or bulk-reset jobs.
3. For a demonstrably unsent, supported dead-letter error, an authenticated admin
   may call `POST /api/admin/whatsapp/jobs/{job_id}/retry` with the trusted frontend
   Origin and existing admin session. This enqueues only; it never calls Meta.
4. The API revalidates configuration, sender scope, snapshot and consent, rejects
   any message ID, acceptance, delivery evidence or send-intent marker, and rejects
   ambiguous-response/delivery, legacy snapshots and changed-business-fact jobs.
   A compare-and-set prevents duplicate replay requests; a counter records replays.
5. Restart the worker only after manual approval and monitor this job. Ambiguous,
   sent/delivered/read or failed-delivery jobs need human provider reconciliation;
   there is deliberately no force-replay endpoint.

## Consent, privacy and webhook security

The repair checkbox defaults unchecked. Missing opt-in is false; truthy strings
are rejected. Timestamp/source/destination are stored with the repair; arbitrary
request recipients are ignored. Before every send the worker rechecks consent.
`DELETE /api/repairs/{id}/whatsapp-consent` is available to the submitting customer
or admin, is idempotent, and prevents pending sends. The customer repair page has
a Stop WhatsApp updates button. Other charger owners cannot withdraw someone
else's consent. Re-consent is not inferred or automatically restored.

Configure HTTPS `/api/webhooks/whatsapp`, the verification token, and Meta's
messages subscription. GET returns the challenge only for the correct subscribe
token. POST validates X-Hub-Signature-256 on original bytes with constant-time
comparison. Limits: 1 MiB and 100 statuses per request. Invalid signatures are
401; unconfigured callbacks are 503; malformed bodies are 400; oversize is 413.
Incoming messages never cause replies. The callback alone bypasses browser Origin
validation; all normal mutating routes retain it.

Uvicorn verification-query logging is redacted, including redirects/encoded query
keys. Redact query strings in ingress/proxy/APM logs too. Keep HTTP wire/body/debug
logging disabled. No template text, customer name, destination, personal data,
credentials or internal notes should enter logs/metric labels. State/error-code
metrics are deliberately aggregate and admin-only. Encrypt database/backups,
restrict operator access and apply the business's retention/deletion policy.
For example, review finished job payload/receipt retention after 30 days, remove
unnecessary personal data, but retain nonpersonal idempotency tombstones for the
entire period source events can be replayed. No automatic TTL deletion is enabled.

## Operations: thresholds and actions

`GET /api/admin/whatsapp/metrics` returns counts and alert booleans, never payloads
or phone numbers. Scrape through an authorized private monitoring path. The worker
logs only `whatsapp_worker_cycle_failed`; alert on repeated cycles/supervisor exit.

| Signal | Initial alert threshold | Action |
| --- | --- | --- |
| Oldest pending/retry job | >300 seconds | Check worker health, provider pause, DB connectivity and queue growth. |
| Dead letters | Any | Inspect safe error code, resolve config/data source; use single-job procedure only when permitted. |
| Expired processing leases | Any | Check supervisor; after restart unmarked work recovers, marked work goes to ambiguous review. |
| Sent without receipt | >1 hour | Verify HTTPS callback/subscription/signature/app/sender configuration; do not resend accepted jobs. |
| Throttled jobs in last hour | >=5 | Reduce throughput, inspect Meta limits and Retry-After; shared cooldown is automatic. |
| Invalid configuration jobs | Any | Keep production disabled; verify all eight mappings, sender and secrets. |
| Embedded outbox repairs / unprocessed receipts | Growing for >5 minutes | Check DB permissions/indexes/reconciliation and sender-mismatched/unknown receipts. |

Counts of throttled jobs represent distinct current job records, not total error
attempts. Tune thresholds with real test traffic; do not weaken consent or security
checks. Missing receipts are not proof of delivery failure.

## Migration, rollout, rollback and manual dependencies

PR #2 is an unmerged dependency at implementation time; this branch includes its
commit. Review the Issue #3 diff against that feature branch, and the combined diff
against repair-mvp. No changes are required on main. Do not run both old and new
workers against the same queue during upgrade.

1. Keep WHATSAPP_ENABLED=false. Back up the DB and stop old workers. Review existing
   unsent v1 events/jobs individually. Schema-v1 snapshots are not sufficient for
   these new templates and will safely dead-letter; do not backfill missing facts
   or change their schema version. Sent/delivered/read history/receipts remain.
2. Configure isolated test DB/app/sender/recipients, real business dispatch address,
   test credentials, supported API version, verified approved mappings, HTTPS
   callback and monitoring. Source history is not replayed when enabling the flag.
3. Follow the eight-event manual checklist in the submission guide only after
   explicit live-test authorization. Confirm payloads, exact customer-visible
   copy, delivery/read webhooks, no-opt-in silence, consent withdrawal and restart
   recovery. Mocks establish code behavior; they do not establish Meta approval.
4. Production requires a separate number/coexistence decision, scoped secret
   provisioning, template approval/classification verification, operator training
   for final balances/courier data, hosting/HTTPS/subscription validation and explicit
   activation review. No payment gateway is integrated by this work. Do not migrate
   the existing personal Business App number as a workaround.
5. For rollback, disable new event creation, stop all workers, keep the signed
   receipt endpoint available, preserve jobs/markers/idempotency state and return
   to the reviewed application version only with sending disabled. Do not run the
   old sender on v2 jobs; it does not understand their safety guards.

Open business decisions: revised published quotes, zero-balance repair routing,
production sender/coexistence, future payment-provider integration and approved
retention periods. These do not block code/tests or require invented configuration.

## Automated validation

Install normal requirements and `requirements-test.txt`. No CI step starts a live
WhatsApp worker; provider requests in tests always use httpx.MockTransport.

```sh
# backend/; use a configured Mongo server with permission to create disposable test DBs
python -m pytest tests/test_whatsapp.py tests/test_whatsapp_lifecycle.py tests/test_whatsapp_mongo.py -q
# Full suite against a separately seeded disposable test API (never production):
WHATSAPP_ENABLED=false REACT_APP_BACKEND_URL=http://127.0.0.1:8001 python -m pytest tests -q -rs
# frontend/
CI=true npm test -- --watchAll=false --runInBand
CI=true npm run build
```

For the full live suite, run the API with a unique disposable DB_NAME, APP_ENV=test,
OTP_MODE=demo, EXPOSE_DEMO_OTP=true and WHATSAPP_ENABLED=false. Keep the original
application database and .env unchanged. Existing auth and Mongo smoke tests also
create/delete their own uniquely named test databases.
