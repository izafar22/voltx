# Lifecycle v3 operations and acceptance

Status: implementation runbook; no live activation or Meta approval is implied. Follow the finalized spec and the repository's explicit authorization rules. Never run the following against a live environment without approval of that operation. Preserve working OTP and the then-current verified production release until a separately approved cutover.

## Readiness and credentials

- API and worker must use the same approved source revision, dedicated environment database, sender, supported Graph version, template manifest and activation UUID. Keep credentials in the existing protected environment file or secret store; never paste, log or commit values.
- The active catalog defines eight customer milestones and nine template variants. All seven unchanged contracts and both REPAIR_RESULT variants need exact live verification: name, locale, Utility classification, body/components, ordered parameters and approved status. The new variant names/copy are proposals until that audit. Do not edit in-review templates or submit missing variants without explicit authorization. The intake wording clarification also needs review against actual approved template copy.
- Populate WHATSAPP_TEMPLATES_JSON from that reviewed manifest. Keep both lifecycle gates false until code, reviewed indexes/control scope, webhook and worker/service dependencies are ready. Authentication OTP continues to use its existing separate template/provider controls.
- `python -m services.lifecycle_readiness` and the default `python -m services.lifecycle_control inspect` are read-only preflights. They report aggregate reasons/index definitions, not secrets, recipients or message bodies. An empty/new queue is not proof that the worker is healthy.

## Reviewed indexes and permissions

`services.lifecycle_readiness.INDEX_PLAN` is the current index plan. API and worker require their documented repair/user/queue/control reads and writes; audit permissions before activation. Starting the v3 worker checks index definitions and refuses missing prerequisites; it does not silently install indexes. Review and install missing queue/receipt/ordering indexes through an explicitly authorized operator change. Do not drop or replace conflicting indexes to make startup pass. Test setup creates indexes only in disposable databases.

## Activation controls

The control CLI defaults to inspect. Mutating actions additionally require `--confirm-reviewed-scope-and-backlog`; this flag acknowledges an already approved operation, not authority granted by this document.

1. Pause/stop the existing lifecycle worker and keep new UI unavailable while preparing an activation. Review aggregate pending/outbox/ambiguous/accepted counts and the intended recipients, consent eligibility, sender/database and templates privately. Never print payloads or bulk-reset/replay jobs.
2. Select a new activation UUID in protected configuration for a fresh scope, alongside the reviewed manifest. Configure the matching API/worker release and gated lifecycle settings only under approved environment changes. No matching active control record means no v3 sends.
3. After approved index readiness and backlog review, the authorized operator may run `python -m services.lifecycle_control activate --confirm-reviewed-scope-and-backlog`. It refuses replacing an unpaused activation or reusing any retired ID recorded for that scope. The control document durably retains canonical used UUIDs; do not delete that history to reuse consent. It binds the new ID and manifest; old jobs/consents do not become eligible or acquire rewritten snapshots.
4. Start the approved supervised worker. The proposed unit is `ops/systemd/rushx-whatsapp.service.example`; replace RELEASE_SHA, inspect user/paths/environment/permissions and review installation before using it. Its preflight is read-only, HTTP timeout is bounded, SIGTERM stops new claims and drains the current request, and systemd stop timeout is 40 seconds. API and worker publish/use the same activation; heartbeat cadence is 15 seconds and capability freshness is 60 seconds.
5. Verify independent API/worker revisions and signed webhook subscription/delivery. Start only with the explicitly approved test/rollout recipients and window. A provider acceptance is not proof of delivery/read. Do not promote a green offline test into a production send authorization.

Staging additionally requires APP_ENV=staging, mode=staging, the existing isolated staging DB/user/host/origin, the default-off STAGING_LIFECYCLE_TEST_ENABLED gate, exact staging sender binding, explicit 1-10 recipient lifecycle allowlist, and WHATSAPP_PRODUCTION_APPROVED=false. API and worker enforce these. An OTP allowlist does not grant lifecycle permission. `activate`/`resume` on staging requires `--test-window-minutes N` (1-120); the control scope expires for dispatch when that window closes. Sender sharing with production OTP needs explicit compatibility review, not automatic credential reuse.

## Pause, resume and recovery

- An authorized `pause --confirm-reviewed-scope-and-backlog` prevents new sends once observed; also stop the worker before deployment/configuration rollback. Keep webhook receipt ingestion available to preserve late real delivery evidence. Already-authorized in-flight sends cannot be recalled.
- A same-ID temporary recovery may use explicit `resume --confirm-reviewed-scope-and-backlog` only after reviewing queue age, consent, recipients, ambiguity and unchanged manifest. A sender/manifest/scope change uses a fresh reviewed activation instead. Expired/superseded jobs are not reconstructed; accepted or ambiguous jobs are not force-replayed.
- Existing admin aggregate metrics include activation/worker health and suppressed/quarantined counts. Review any dead letters, stale heartbeat, queue lag over 300 seconds, expired leases, or accepted jobs missing receipts over one hour. Never expose these endpoints publicly or add recipient data to alerts.
- The existing single-job retry API remains admin/Origin protected and schedules only demonstrably unsent supported failures. v3 adds current identity, consent, activation, freshness and sequence checks. No force-replay endpoint or bulk snapshot rewrite is provided.
- Restore the approved previous frontend/backend/worker pair only after pausing enqueueing/dispatch and retaining queue/receipt evidence. Older runtime code lacks the v3 eligibility checks: keep its lifecycle sender disabled and its worker stopped. Do not rotate OTP credentials, rewrite customer phones, delete profile/payment data or perform a live migration as a side effect. Existing session/linking-challenge rollback caveats remain applicable.

## Authorized staging evidence checklist

Exercise the full positive-balance eight-message API journey with real approved templates and allowed test recipients, then the alternate verified-zero completion variant separately. Verify team acceptance before inbound instructions; default opt-out/withdrawal; phone replacement and in-flight boundary; actual estimate approval; authoritative balance and receipt; confirmed courier/tracking; no standalone completion/payment-pending duplicate; receipt correlation; restart/throttling/expiry/old-scope suppression and isolated rollback. Record redacted content plus actual sent/delivered/read evidence and limitations. Read receipt absence is not a failure claim. The zero-balance onward-return transition is outside this change; do not invent a payment to bypass that existing lifecycle limitation.

No automatic reminder, existing-repair re-enrolment or retention deletion job is installed by this feature. The proposed privacy/retention process requires its own review and authorization.

Notification construction failures in payment flows are logged with fixed reason codes; balance/receipt persistence still commits together with a bounded immutable notification intent for eligible v2 consent. Reconciliation recovers that intent once, retaining its original event time, 24-hour deadline, source revision, consent and balance/receipt snapshot. Completion is reserved in that same payment write. Expired intents become terminal deduplication records; no new deadline or old-scope consent is created. Pending earlier intents hold later dispatch until recovered or expired. Raw intents are never returned by repair APIs. Transient activation reads during dispatch defer demonstrably unsent work without consuming attempts; a pre-HTTP intent is cleared before retry, while actual ambiguous provider attempts retain their existing protection.

Repair consent also binds the sender/environment/database scope. Reusing an activation UUID in a different sender scope cannot authorize existing consent. Registered chargers without a stored name remain reportable; acknowledgement copy uses a neutral registered-charger description rather than inventing a brand.

Intent recovery scans bounded batches in _id order with a rotating worker cursor; after the end it wraps and revisits deferred work. Targeted repair-ordering recovery leaves the global cursor unchanged. This prevents a batch of old-scope intents from blocking later eligible repairs, without deleting intents during an outage.

## Live contract readiness (audited 2026-11-20)

Active v3 configuration pins the audited en locale and two-parameter request acknowledgement; legacy transport fixtures retain their original en_US contract. Reuse only the five exact compatible audited templates. The four new approved-for-submission templates still need actual Meta approval. Staging uses its explicitly bound sender/allowlist and does not require a separate Meta test-number ID; test/production modes retain that guard.

For a shared sender, the staging webhook persists only receipts matching known staging jobs with a send intent or accepted provider ID, matching sender and any supplied recipient. It still accepts genuine early or late receipts while sending is paused. Unrelated OTP/other-environment notifications are not persisted in staging. Inspect existing app callback/subscriptions and publication state before changing routing; preserve the older global callback unless a separately reviewed change authorizes replacement. A staging-specific WABA callback override and app publication each require their concrete account/routing readiness review.
