# WhatsApp lifecycle updates — implementation task plan

Prepared 2026-11-20 from the finalized [requirements](requirements.md) and owner-approved [design](design.md), including the approved eight-message amendment and existing RushX logo. Status: IMPLEMENTATION AUTHORIZED on 2026-11-20. Owner instructed proceeding with the task plan; offline implementation and verification are authorized. Offline implementation and validation are now recorded in validation.md. Live templates, service configuration, indexes and data have not been changed.

The eight customer messages are request received, accepted-for-inspection/inbound instructions, charger received, estimate ready, estimate approval confirmed, combined repair completion/verified balance, payment received, and return dispatched/tracking. The combined milestone has mutually exclusive positive- and zero-balance template variants; it does not send both. Internal repair statuses remain distinct.

## Specification gates and approvals

| Gate | Status | Evidence / next action |
|---|---|---|
| Source audit | DONE | Existing worker/outbox, catalog, auth/payment/repair integration reviewed; historical inventory retained in design.md |
| Requirements | DONE | PR #72 merged; owner approved eight-message amendment on 2026-11-20 |
| Design and UI direction | APPROVED | Owner approved the UI with canonical RushX logo, then design and amended message set; detailed combined-event design recorded |
| Implementation task plan | APPROVED | Owner instructed proceeding with the task plan on 2026-11-20 |
| Runtime implementation / code review / CI | DONE (#74) | Merged b978723 and staging release 492 verified; live contract compatibility follow-up in progress |
| Merge / authorized staging sends | MERGED; STAGING TEST APPROVED | #74 merged with owner approval. Owner approved staging setup and one recipient for a 60-minute window after readiness; window not started and no sends |
| Production promotion / deployment / activation | NOT AUTHORIZED YET | Approved release version, promotion PR into new release branch, final-SHA CI/artifact approval and operator verification |

## Dependencies

| Task | Deliverable | Depends on | Status |
|---|---|---|---|
| WL-01 | Active eight-milestone/template contracts and snapshot schema | Task approval | DONE (offline) |
| WL-02 | Explicit team intake acceptance and customer next-step contract | WL-01 | DONE (offline) |
| WL-03 | Verified phone generation and consent-capability binding | WL-01 | DONE (offline) |
| WL-04 | Repair-specific consent state, withdrawal and safe projections | WL-03 | DONE (offline) |
| WL-05 | Combined completion/verified-balance event and durable reservation | WL-01, WL-04 | DONE (offline) |
| WL-06 | Fenced ordered dispatch, freshness, suppression and replay | WL-02, WL-04, WL-05 | DONE (offline) |
| WL-07 | Shared API/worker staging isolation and activation controls | WL-01, WL-06 | DONE (offline) |
| WL-08 | Worker supervision, readiness, monitoring and recovery runbooks | WL-06, WL-07 | DONE (offline) |
| WL-09 | Consent, verification, team acceptance and repair-detail UI | WL-02, WL-03, WL-04 | DONE (offline) |
| WL-10 | Integrated regression / concurrency / UI verification | WL-05 through WL-09 | DONE (offline) |
| WL-11 | Code review, CI and merge evidence | WL-10 | DONE (#74, staging verified) |
| WL-12 | Live template audit and authorized staging acceptance | WL-08, WL-11, explicit operational approvals | IN_PROGRESS (see staging-acceptance.md) |
| WL-13 | Selected production release, verification and activation | WL-12, explicit release/activation approvals | PLANNED |

## WL-01 — Message and snapshot contracts

Reuse the existing whatsapp_service/catalog and payment event interfaces. Define the active logical set of eight messages; keep CUSTOMER_APPROVED and PAYMENT_RECEIVED. Replace the two legacy standalone notification mappings with one REPAIR_RESULT milestone and the two proposed template variants from design.md. Preserve existing internal REPAIR_COMPLETED/PAYMENT_PENDING statuses and historical source/template records; legacy jobs remain ineligible for new activation.

Add snapshot v3 fields, immutable variant/manifest/activation/consent bindings, occurred_at, post-write source_revision and expires_at. Define safe typed reason codes and supported schema boundaries in shared helpers. Keep exact body parameter order and data minimization; no real customer fixture values or claims that proposed templates are approved. Active readiness verifies all required variants, not the old two standalone entries.

Acceptance/tests: exact seven unchanged payloads plus both REPAIR_RESULT variants; positive amount required for amount_due variant, no payment parameter in zero variant; unknown/invalid balance rejected; unsupported/legacy schema, wrong template variant/manifest and production hello_world fail closed. Catalog and mapping contract tests distinguish eight messages from nine active template variants.

## WL-02 — Team acceptance and next steps

Remove customer/owner permission to set AWAITING_SHIPMENT and the repair form's automatic transition. Reuse the existing status endpoint with explicit admin acknowledgement and a server-validated instruction-preview digest. Persist intake_acceptance, history, revision and any eligible event atomically. Require a real facility instruction snapshot independent of WhatsApp availability. Same accepted snapshot retries do not produce another event; conflicts refresh safely. Update customer-safe detail projection and legacy awaiting-shipment behavior.

Acceptance/tests: new requests remain REQUESTED; ordinary/old clients cannot accept; admin confirmation/address digest and CAS enforced; concurrent acceptance/retries; no address/changed preview; successful acceptance when messaging is down; instructions only after acceptance. Preserve legitimate transit/estimate/cancellation permissions. No acceptance or message backfill for legacy records.

## WL-03 — Verified identity and capability binding

Add phone_generation lazily and atomically to the existing successful number-changing user write, retaining the current auth_epoch/session-retention and challenge-purpose guarantees. Same-number login/verification must not change it. Build authenticated no-store capability discovery and a short-lived purpose/session/user/phone-generation bound consent selection token. Refresh the current account before eligibility decisions; do not expose secrets/sender details. Define idempotent creation lookup before mutable binding checks on an exact ambiguous retry.

Acceptance/tests: Google-only/WhatsApp/linked accounts, absent/unverified phones, same-number login, change away/back, ownership conflict, expired/wrong-purpose/cross-user/session bindings, account change during submission and persisted creation retry. Existing session-retention/revocation and OTP suites remain green. Preserve owner-role repair access without opening customer-only link operations.

## WL-04 — Consent and response privacy

Persist server-owned repair consent v2 and derive customer-visible effective states. Preserve opt-out defaults, draft-safe stale-identity recovery, no retroactive opt-in and no re-enable/retarget for existing repairs. Extend withdrawal revision/CAS and effective phone-change pause. Create events only for an eligible currently bound submitter; a worker/config outage does not revert a valid business mutation. Return actual requested/effective state, never a delivery claim.

Acceptance/tests: opt-out, consent/source/revision validation, repeated withdrawal, worker-down withdrawal, cross-user/support permissions, invalid arbitrary recipients, phone-change race boundary, no automatic consent recovery when old digits return, and customer/owner redaction. No raw consent, tokens, actor data or queue payloads leak through API/metrics/logs.

## WL-05 — Combined completion and balance

Do not enqueue standalone completion or payment-pending notices. Extend the existing authoritative balance-attestation CAS write to reserve completion_notice and append REPAIR_RESULT once a completed repair has a verified reconciled balance. Use deterministic repair_id:REPAIR_RESULT across both variants, status changes, concurrent writers and retries. Preserve that reservation after reconciliation/suppression/privacy cleanup. Use verified_balance_summary with non-negative money validation; the current positive-only amount_due helper remains the PAYMENT_PENDING business guard.

Freeze the balance-attestation identity, selected variant and immutable values at first eligible reservation. No verified balance means no completion message; recording completion alone cannot create a placeholder. Later updates cannot send another completion notice or rewrite its amount. A later settled balance suppresses an unaccepted positive notice; the independent verified receipt may still acknowledge payment. No receipt is invented for a zero attestation, and no new lifecycle edge is added to work around the known zero-balance onward-shipping limitation.

Acceptance/tests: completion-before-balance, positive/zero/unknown balances, pre-completion/invalid/non-finite/negative inputs, concurrent same/different attestations, repeated completion/status saves, crash/reconciliation recovery, one durable reservation, payment settling before/after send, unchanged full-receipt/idempotency/UTR handling and no false payment acknowledgement. Deadline begins at first eligible combined event and never refreshes on repeated saves. Zero-balance notification is tested without claiming an unsupported full return journey.

## WL-06 — Dispatch, ordering and freshness

Reuse leased/fenced jobs and outbox reconciliation. Add namespaced per-repair dispatch control and source-revision ordering, including earlier embedded outbox items. Apply the design's 24-hour send-attempt deadline and per-message business freshness checks. Add suppressed/quarantined terminal outcomes without erasing provider receipts. Validate activation, current account phone/consent and both lease fences immediately around durable send intent as specified in design.md.

Preserve bounded transient retries, shared throttling, Retry-After handling, no blind ambiguous replay, receipt deduplication/ranking and existing safe single-job replay restrictions. Replay shares all new eligibility/freshness/order checks. Do not promise atomic MongoDB/Meta revocation: tests must expose the in-flight race limit, not disguise it.

Acceptance/tests: standalone MongoDB concurrency, two workers/leases, stale fences and suspended worker, earlier outbox vs later job, expiry and superseded prompts, balance/receipt changes, withdrawal/phone/pause before and after the final checks, crash before/after intent/acceptance persistence, malformed success, 429/5xx, reordered receipts and no automatic duplicate accepted message. An ambiguous earlier attempt must not block all later valid milestones forever.

## WL-07 — Activation and staging isolation

Implement shared API/worker validation for dedicated mode=staging with default-off gate, dedicated data, explicit lifecycle allowlist and exact sender binding. Keep production approval false in staging; OTP permissions grant no lifecycle consent. Pin activation IDs and validate the shared scope/manifest at enqueue, reconciliation, claim, retry and replay. Add explicit reviewed pause/resume/new-activation operations with aggregate backlog classification; no old-job/consent rewrite or automatic historical send.

Acceptance/tests: API and worker startup/dispatch negatives for wrong mode/sender/DB/user/origin, malformed/empty/over-limit allowlists, stale/missing/mismatched activation or manifest, old/test jobs, and replay attempts. Preserve existing staging OTP allowlist/sign-in behavior and production guards. Prove new activation does not drain existing backlog and same-ID temporary recovery retains freshness/consent checks.

## WL-08 — Worker and operator readiness

Provide read-only config/index/template-manifest readiness checks, reviewed index definitions and isolated index tests, worker heartbeat/version, safe aggregate monitoring, SIGTERM stop/drain and a non-root Oracle service/runbook proposal bound to the same release as API. Existing index creation/startup behavior must not become an unreviewed live migration. Document required DB permissions, environment references and webhook query-token redaction. No service installation, index mutation or environment change is performed as part of offline implementation without explicit operational authorization.

Acceptance/tests: idle heartbeat, throttling while heartbeating, missing indexes/definition conflict, stale heartbeat (60 seconds), heartbeat cadence (15 seconds), 20-second HTTP bound, 40-second supervisor shutdown plan, lease/intent preservation on termination, recovery and read-only readiness privacy. Monitoring distinguishes worker down, queue empty, expired work and accepted-without-receipt. Retention is a reviewed proposal; no automatic production cleanup/TTL job is activated.

## WL-09 — Customer/admin UI

Reuse existing Logo.jsx, shell, profile phone dialog, canonical tokens and component variants. Build the approved unchecked consent UI and actual eligibility/effective states. Preserve charger/photo/address draft during phone linking; refresh/clear consent selection when identity changes. Make successful submission remain REQUESTED with wait-for-review copy. Provide explicit team acceptance/instruction preview/confirmation and replace unconditional customer shipping instructions with state-based next steps. Keep estimate approval on WhatsApp as well as its dashboard confirmation. Show stopped/paused/unavailable states and accessible withdrawal/error recovery without an existing-repair re-enable button.

Acceptance/tests: React interactions plus browser checks at 320/375/768/1280, both themes, keyboard focus/labels/loading/errors; draft/default/creation-retry integrity; canonical logo reuse; admin-only acceptance; actual returned consent state during service outage; old-client/legacy record behavior; correct requested/accepted/estimate/return/exception next steps. Storybook uses the production components rather than a parallel mock implementation.

## WL-10 — Integrated verification

Run repository backend, frontend, build and browser/Storybook quality gates against a disposable API/MongoDB and mocked provider transport. Exercise all eight positive-balance milestones end to end and the alternative verified-zero completion variant separately. Include duplicate submissions/acceptance/balance attestation, published estimate approval, full verified receipt, actual confirmed return-shipment facts, opted-out and withdrawn journeys, phone generation, stale instructions and environment isolation. No production DB or live Meta HTTP in automated tests.

Acceptance: exact commands/results recorded in validation.md, including skips and warnings; no invented passes. Audit final diff for secrets/PII, unintended lifecycle/payment/auth changes, parked functionality, migrations, schema/config defaults and external template assumptions. Each requirement has explicit test evidence or a named authorized live/manual acceptance step.

## WL-11 — Review and integration

Open implementation PR against repair-mvp with scope, actual test evidence, risks, compatibility, rollout/rollback and updated context. Resolve review findings, rerun checks justified by fixes and obtain explicit merge authorization. Keep incomplete consent controls/worker dispatch unavailable until dependencies are ready. After merge, observe automatic staging CI/CD and verify exact frontend/backend revisions and service state through the restricted lookup. Do not equate a green offline suite or merged PR with real provider delivery.

## WL-12 — External audit and authorized staging acceptance

Read the current live template inventory in the intended Meta account through authorized read-only access and compare exact names/locales/category/full components/order/status. Record a redacted manifest and current supported Graph-version compatibility without rotating working OTP credentials. The two combined templates are proposals, not existing approvals. Any submission/edit requires explicit authorization; never modify templates already in review autonomously.

After explicit staging environment/index/service and recipient/window approvals, validate isolated worker/webhook readiness and exercise all eight messages, plus the alternative verified-zero template. Capture redacted content and receipt evidence; do not assume read receipts. Confirm acceptance-first, no duplicate standalone completion/payment notice, withdrawal/phone-change/outage behavior, pause/resume/backlog isolation and paired rollback rehearsal. Document missing or blocked external evidence rather than claiming completion. Lifecycle test sender choice/shared OTP effects need an operator-reviewed decision before sends.

## WL-13 — Production release and activation

Agree the version and selected production scope only after staging acceptance. Verify active component revisions, create a new release branch from that baseline, create a promotion branch with only approved commits/dependencies, and PR into the new release. Merge with owner approval and test/package the final merged SHA. Obtain approval of the exact artifact/backend/worker combination before deployment. Do not merge into historical baseline branches or deploy an unmerged feature candidate.

Prepare protected backups, active-schema/index readiness, a reviewed backlog/consent cutoff, supervised worker configuration and explicit activation/first-recipient plan. Production deployment, environment/index/template changes and provider sends each require their applicable explicit authorization. Verify both component SHAs, worker version and public/auth boundaries; report actual provider delivery evidence separately. Rollback disables lifecycle sends/stops worker first, preserves evidence and OTP/repair access, and restores the approved pair; no bulk replay, customer-data rewrite or automatic old-worker restart.

## Deferred work

Public repair-journey marketing/site redesign, automatic reminders, new exception messages, partial-payment/refund/revised-estimate flows, zero-balance onward-return transitions, message variants for later balance adjustments, existing-repair re-consent/retargeting and autonomous retention cleanup remain outside this task plan. Raise a concrete requirement change if a dependency requires any of them; never silently expand scope.
