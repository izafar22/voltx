# PR #4 pre-merge safety gate — 2026-10-22

Branch `codex/rushx-whatsapp-lifecycle`, base `repair-mvp`. Reviewed PR comment
6333250514 and complete Issues #6/#7 against commit afe3b8b before changing code.
**Recommendation: NO MERGE / NO DEPLOY until the remaining risks below receive
explicit review.** This report does not close either issue or authorize activation.

## Evidence and reconciliation

Line references below are to this safety-gate revision; paths are relative to backend.

| Finding | Status in this revision | Evidence |
| --- | --- | --- |
| #7 status/history/outbox race | Already fixed; retained | `server.py:827`, `repair_guard`: one revision/status CAS; existing competing-transition and real-Mongo tests |
| #7 mutable published quotes | Already fixed; retained | `server.py:892`: non-DRAFT edit rejected; publishing uses CAS; existing quote immutability tests |
| #7 diagnosis race/state guard | Fixed | `server.py:876`: inspection-stage guard, revision CAS; `tests/test_safety_gate.py:202` forces concurrent closure |
| #7 draft estimates on closed repairs | Fixed | `server.py:892`: drafting limited to pre-publication inspection stages; terminal edits rejected |
| #7 monetary precision | Fixed for new writes, legacy retained | `services/repair_facts.py:111` exact input validation; `server.py:909` immutable INR total/fee/part minor-unit snapshots alongside compatible numeric fields. Decimal arithmetic remains authoritative; fractions of paise and booleans rejected |
| #7 duplicate repair creation | Fixed for keyed requests | `server.py:727`: user-scoped fingerprint/unique sparse creation key; same key/body replays, changed body conflicts. React keeps the key across ambiguous retries. Concurrent creation regression ensures one repair/history/outbox. Legacy callers omitting keys remain supported and are not deduplicated |
| #7 bounded listing/pagination/indexes | Fixed server paging | `server.py:785`: 1–100 row cursor pages, deterministic timestamp/ID order, bounded DB projection excluding photos and private audit blobs; `services/safety_indexes.py:2` user/status/charger/date indexes. Existing React consumers follow cursors, preserving the array contract |
| #6 unsupported scopes/roles and malformed ownership | Fixed | `server.py:669`, `683`, `785`: default-deny checks; negative cross-role/user tests |
| #6 charger-owner IDOR | Fixed mutation/privacy gaps | Owners may read a minimal equipment status projection for their charger, but may not edit another customer's repair, payment or consent. `server.py:683`, `695`; cross-owner test at `tests/test_safety_gate.py:108` |
| #6 inbound vs return permissions | Return restriction already fixed; inbound fixed here | `server.py:922`: customer inbound edits only before receipt; no customer received/delivered confirmation; closed repairs locked. Return confirmation remains admin-only with existing post-dispatch tracking lock |
| #6 private fields | Fixed additional leaks | `server.py:695`: non-admin responses remove internal shipment/estimate notes and history note/actor fields; linked owners receive only ID/number/charger/status/timestamps. Payment audit/reference/WhatsApp fields already hidden |
| Production mock top-up | Fixed | `server.py:202`, `214`: explicit development/test-only guard before any write; production-denial regression asserts zero financial records |
| Similar simulated finance | Fixed by production disablement, not a new ledger | Same guard on charging session start/stop, owner withdrawal, admin wallet adjustment and withdrawal status update. These paths simulate energy, balances or payout and cannot be treated as verified financial settlement. Existing non-production demos remain usable |
| Payment index creation on each request | Fixed | Unique payment index moved from `PaymentRepository.reserve` into `initialize_safety_indexes`, called at API startup before auth/demo seed. No destructive migration |
| Payment RESERVED/CAS/APPLIED failure windows | Already fixed; verified again | `services/payment_service.py:246`, `372`, `400`, `417`: exact retry rechecks balance/state/consent; atomic aggregate receipt/event/outbox; marker repair after commit. Crash, overlapping-writer, duplicate UTR/key and real-Mongo tests retained |
| PAID without funds / duplicate settlement | Already guarded; retained | Customer evidence never settles; admin confirmation and full positive exact amount required. Unique UTR across repairs/electronic methods; one receipt per repair |
| Paid repair cancellation | Fixed fail-closed rule | `server.py:843`: cancellation after receipt requires reviewed refund handling; it cannot silently hide a paid repair |
| #7 revised quote / zero balance / refund workflows | NOT implemented | Published quotes stay immutable; no re-quote endpoint, zero-balance routing shortcut, partial receipts, refund or reversal. Existing safe refusal retained instead of changing lifecycle/payment semantics without business review |
| #6 separate technician/operations/finance roles; MFA/dual control; role-change audit | NOT implemented | MVP consolidates staff into existing admin. These require auth/operational decisions; no role migration or MFA system introduced |
| #7 live load, p95/p99 targets, mobile/accessibility acceptance | NOT performed | No representative staging workload, devices, or approved performance SLO supplied. No production probes performed |

Reporting a fault on a registered public charger is an existing customer workflow,
not ownership transfer. It remains allowed; submission creates a repair owned by the
caller and grants no access to anyone else's repair. A proposed owner-only submission
restriction was rejected after regression tests demonstrated that incompatibility.

## Permission matrix (MVP)

| Action | Customer / owner as submitter | Owner linked to someone else's repair | Consolidated admin | System worker |
| --- | --- | --- | --- | --- |
| Create repair, report public charger | Yes; owns new repair | Can create own report | Yes | No API identity |
| Read/list | Own repairs, filtered | Minimal equipment status only | Full authorized operations view | DB access only as provisioned |
| Customer status actions | Existing permitted graph/actions | No | Existing graph, CAS | No |
| Diagnosis / estimate | No | No | Inspection stages only; published quote locked | No |
| Incoming shipment | Pre-receipt courier/tracking/shipped information; cannot confirm receipt | No | Staff confirmation; terminal lock | No |
| Return shipment | No | No | Existing confirmed tracking workflow, terminal lock | No |
| Balance / funds receipt verification | No | No | Finance duty consolidated into admin; audit and exact-match checks | No |
| Submit unverified UTR | Own repair only | No | Only if also the submitter | No |
| Consent withdrawal | Own repair | No | Support allowed | Checks current consent only |
| Notification retry/metrics | No | No | Existing admin endpoints | Existing durable job leases/outbox |

No new roles or silent privilege migration. Existing admins remain trusted for both
operations and finance; review that consolidation and compensating controls before
launch. Browser controls are not authorization boundaries.

## Migration, recovery, and rollout restrictions

Startup creates only non-destructive indexes. A duplicate legacy key or index failure
must fail startup for operator review; code never deletes or rewrites conflicting
data. Provision index permissions or pre-create identical indexes before rollout.
No production database was contacted for migration. Mock tests explicitly initialize
indexes when bypassing FastAPI lifespan; real-Mongo tests use disposable databases.

Payment recovery remains documented in [PAYMENTS.md](PAYMENTS.md): RESERVED does not
mean PAID; exact authorized retries recover the operation, and conflicting facts
require audited review. No background auto-settlement or automatic reservation
release was added. Back up repair aggregates and reference records together.

WhatsApp flags remain disabled by default and the existing production gate, sender
isolation, explicit opt-in, signatures and async worker stay unchanged. Payment and
repair routes write durable events, not provider HTTP. No sender, number, template,
credential, production data, live message or activation configuration was changed.

## Security/dependency checks and remaining risks

Dependency follow-up for comment **6336573688**, starting at `4ae54c8`:

| Check / change | Result |
| --- | --- |
| Declared production package manager | Yarn 1.22.22; fresh isolated frozen install validated. Actual production installer is not evidenced in this repository |
| Browser dependency fixes | Axios 1.20.0 and React Router 7.18.2; no React/CRA major upgrade |
| Build/dev dependency fixes | Targeted same-major patches, including critical proxy-addr and shell-quote; existing resolutions retained |
| Yarn audit, unique advisories | Before: 2 critical / 34 high / 19 moderate. After: **0 critical / 3 high / 3 moderate** |
| Yarn audit, path occurrences | Before: 3 critical / 110 high / 50 moderate. After: **0 critical / 13 high / 16 moderate** |
| npm retained lock audit | **116 entries: 2 critical / 73 high / 35 moderate / 6 low**, unchanged. npm ignores Yarn resolutions; this graph is not tested or approved for release |
| Python fixes | certifi 2026.10.19, PyJWT 2.15.0, urllib3 2.8.0; isolated runtime pip check passes |
| pip-audit 2.10.1 | Before: 29 records / 20 unique IDs in 8 packages. After: **23 records / 14 unique IDs in 5 packages**. Pinned-list scan, not full transitive/OS coverage |
| Verified Host/path middleware vulnerability | Use routed ASGI path for origin, auth validation and no-store checks; three tests fail on old code and pass on fixed code |
| Complete backend | **246 passed, 2 existing skips**, 11 warnings; disposable test DB, WhatsApp disabled |
| Frontend / production build | **134 tests, 12 suites passed; build compiled successfully** |
| Remaining fixes requiring incompatible upgrades | SVGO 1.x/CRA, FastAPI/Starlette; Mongo driver/Motor compatibility review. No forced upgrades |
| Merge recommendation | **HOLD** pending reviewer disposition of residual risks and prior safety-gate decisions |
| Deployment recommendation | **NOT READY**: installer verification, residual Python assessment and operational gates remain |

See [dependency triage evidence](DEPENDENCY_SECURITY.md) for every critical/high
Yarn advisory's installed version, dependency chains, patched range, exposure and
disposition; Python findings, exact commands, remaining risks and test limitations.
No dependencies were removed, no package manager switched, and no live messages,
Meta changes, production mutations, merge or deployment occurred.

Live 100/1000 requests-per-day load tests, p95/p99/error-budget measurement, physical
mobile/accessibility acceptance, real Meta template/delivery verification, merchant
QR/account ownership verification and production backup/restore drills were not run.
No safe staging authorization or real payment/message was inferred from this task.

Remaining scale limitation: the frontend automatically accumulates cursor pages to
preserve its existing all-rows UI; virtualized/manual paging and very large charger
owner membership sets still need representative load testing. Clients must retain
and reuse creation idempotency keys across retries; legacy unkeyed calls cannot be
safely deduplicated by guessing user intent.

## Validation

| Check | Result |
| --- | --- |
| Complete backend `python -m pytest tests -q -rs` | **243 passed, 2 existing skips**, 96.11 seconds |
| Focused safety-gate regressions | **21 passed** |
| Frontend `CI=true npm test -- --watchAll=false --runInBand` | **134 passed, 12 suites** |
| `CI=true npm run build` | **Compiled successfully** |
| Pyflakes / compileall / diff whitespace | Passed |
| `python -m pip check` | No broken requirements |
| `npm audit --json` | Completed, nonzero exit: **116 advisory entries**, unresolved |
| Python vulnerability scan | Not run: pip-audit unavailable |

Two existing backend skips concern an empty owner wallet and absent withdrawals.
Warnings include existing FastAPI/multipart deprecations and a mongomock duplicate-
index test deprecation; no failed tests remain. No pytest worker configuration changed.

The final commit SHA is recorded in the PR review summary. Backend tests
use a locally started isolated test API and fresh disposable MongoDB databases;
all Meta HTTP is mocked. Frontend suites and production build run locally. No
production data writes or real payment transactions are part of validation.

Please review the safety-gate diff and unresolved requirements before authorizing
merge. Leave PR #4 and PR #2 open. Passing tests do not override the no-merge/no-deploy
recommendation while dependency and business/operational gates remain unresolved.
