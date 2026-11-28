# SEO-000 — Existing harness discovery and reconciliation

Status: DISCOVERY ONLY — independent review verdict **CONDITIONAL PASS**.
The owner supplied that verdict in the SEO-000.02 reconciliation request on
2026-11-28. The existing specification-based integration is architecturally
accepted; final discovery acceptance remains with the independent reviewer.
No SEO requirements, master strategy, implementation, merge or deployment is
approved by this document.

## 1. Inspection scope, revisions and provenance

| Inspection | Date (India) | Branch/ref | Exact revision |
|---|---|---|---|
| Original read-only discovery | 2026-11-28 | `docs/customer-profile-staging-acceptance` | `5206722af8a939d903946f0bdef5dfea51104bf1` |
| Revalidated integration baseline | 2026-11-28 | fetched `origin/repair-mvp` | `b21e3277f1ac57c315936f34228a1a908bffc759` |
| Persistence branch | 2026-11-28 | `docs/seo-workstream-discovery` | Created directly at the recorded integration baseline in a separate managed worktree |

Repository: `izafar22/voltx`; website: `https://evchargerrepair.in`.
The original discovery was delivered in chat and did not create repository files.
This document preserves its substantive findings, recommendations and limitations,
and reconciles them against the approved base rather than treating the old
checkout or its local changes as integration truth.

Evidence labels used throughout:

- **Verified:** inspected repository contents, Git comparisons or GitHub metadata.
  Source presence is not proof of runtime activation or successful execution.
- **Historical:** dated repository records or owner/operator reports; not repeated
  in this inspection.
- **Proposed:** future structure or workflow, not implemented or approved SEO work.
- **Unknown:** not established by this inspection.

The original tree had unrelated modifications to `context/progress-tracker.md`,
`specs/customer-profile/tasks.md` and `specs/customer-profile/validation.md`.
Those contained newer customer-profile acceptance statements. They were not
incorporated into this branch or used as authoritative baseline evidence.
The original tree remains on its original branch and SHA. Its complete tracked
binary diff fingerprint before work was SHA-256
`d32abf8526d6347ae77d21efe5894fca59f0cf77892d5ca50a940bc510091f18`.
No stash, reset, discard or overwrite was used.

The new branch was absent locally and on origin before creation. A targeted
`git fetch origin repair-mvp` established the exact base above. There are 29
commits reachable from that base but not the original SHA; their aggregate diff
contains 87 changed paths. This is an aggregate comparison and targeted source
inspection, not a line-by-line audit of all application changes.

Revision-pinned evidence roots:
[original checkout](https://github.com/izafar22/voltx/tree/5206722af8a939d903946f0bdef5dfea51104bf1),
[revalidated baseline](https://github.com/izafar22/voltx/tree/b21e3277f1ac57c315936f34228a1a908bffc759),
[comparison](https://github.com/izafar22/voltx/compare/5206722af8a939d903946f0bdef5dfea51104bf1...b21e3277f1ac57c315936f34228a1a908bffc759).

## 2. Existing harness architecture and all twelve discovery areas

The verified harness is document based: agent instructions, shared context,
per-workstream specifications, validation evidence, a dated handover, Git/PR
history and operational runbooks. No executable session loader, automatic
checkpoint engine or unified machine-readable workstream manifest was identified
in the inspected tracked harness files. This is a scoped finding, not proof that
no external integration exists.

| Area | Verified repository mechanisms and evidence | Boundaries/gaps |
|---|---|---|
| 1. Agent instructions | Root [AGENTS.md](../../AGENTS.md); [workflow rules](../../context/ai-workflow-rules.md); additional legacy instructions in [test_result.md](../../test_result.md). One AGENTS.md was found in the inspected checkout. | Distributed older instructions need interpretation against current entrypoint and user authorization; none were overwritten. |
| 2. Persistent memory | Six files in `context/`, `specs/`, operational `docs/`, [project handover](../../docs/RUSHX_PROJECT_STATE.md), Git history. | [memory/PRD.md](../../memory/PRD.md) describes the older VoltGrid charging-network product, not the current repair-focused authority. Preserve history; do not create SEO memory there. |
| 3. Manifests/state | [spec registry](../README.md), [shared progress tracker](../../context/progress-tracker.md), spec task documents; frontend package manifests/locks; visual asset manifests; staging-generated `release.json`. | Asset, dependency and deployment manifests have distinct roles; no unified project-state schema was identified. |
| 4. Session initialization | AGENTS requires the six context files in order, then relevant source/tests and Git inspection. The handover has a new-chat resume protocol. | Manual recovery; no verified automatic loading or ChatGPT-to-repository synchronization. |
| 5. Checkpoint/handoff | Handover records date, SHA/ref, PRs, checks, deployment/rollback, unresolved items and next step; requires session-end updates. | Dated snapshot, not automatic/live state; no checkpoint enforcement identified. |
| 6. Task/execution workflow | [specs/README.md](../README.md) prescribes requirements, design, task review before implementation. [Customer-profile tasks](../customer-profile/tasks.md) demonstrate IDs, dependencies, status, acceptance and separate merge gates. | No full SEO backlog/phases yet. Newer workstreams extend the same model rather than replacing it. |
| 7. Evidence/verification | [code standards](../../context/code-standards.md), [customer-profile validation](../customer-profile/validation.md), CI, screenshots, topic QA and deployment smoke checks distinguish claims from evidence. | SEO evidence provenance, metric definitions, reporting windows and freshness rules remain to be designed. |
| 8. Decision logging | Spec design sections, dated requirements/task approvals, handover risk/uncertainty notes. [Customer-profile design](../customer-profile/design.md) has approved decisions. | No adopted central ADR registry identified at this base; open PR #61 proposes one (section 5). |
| 9. Automation/CI/CD | Three workflows in `.github/workflows/`, deployment helpers in `scripts/`, historical `.emergent/cron/` preview scripts. | Workflow presence does not establish live environment settings, credentials, reviewer protection or current success. |
| 10. Documentation conventions | Lowercase hyphenated `specs/<name>/`; canonical requirements/design/tasks, validation precedent, topic evidence directories. Existing older specs remain in `docs/`. | Link to canonical content; do not copy specs into docs or reorganize legacy material incidentally. |
| 11. Multiple workstreams | Shared progress rows, spec registry, feature branches, PRs, per-spec tasks/validation; parked features explicitly separated. | Cross-workstream ownership/dependencies remain manually managed; registry is incomplete (section 4). |
| 12. Independent recovery | Entry rules → six context files → relevant spec/tasks/validation → handover/runbooks → source/Git/runtime evidence when needed. | Codex needs the right checkout; ChatGPT needs repository access or a revision-labelled snapshot. Chat history alone cannot synchronize Git. |

Required context reading order remains unchanged:
`ai-workflow-rules.md`, `project-overview.md`, `architecture.md`,
`code-standards.md`, `ui-context.md`, `progress-tracker.md`.
The root entrypoint and these six files were read again at the reconciled base.

Pinned harness evidence:
[entrypoint](https://github.com/izafar22/voltx/blob/b21e3277f1ac57c315936f34228a1a908bffc759/AGENTS.md),
[workflow](https://github.com/izafar22/voltx/blob/b21e3277f1ac57c315936f34228a1a908bffc759/context/ai-workflow-rules.md),
[registry](https://github.com/izafar22/voltx/blob/b21e3277f1ac57c315936f34228a1a908bffc759/specs/README.md),
[handover](https://github.com/izafar22/voltx/blob/b21e3277f1ac57c315936f34228a1a908bffc759/docs/RUSHX_PROJECT_STATE.md).

## 3. Reusable capabilities and verification infrastructure

Verified source capabilities (not current deployment claims):

- `backend/services/studio_cms.py` fetches CMS content and renders blog/posts,
  Studio pages, sitemap and `llms.txt`, with revalidation and SPA fallback rules.
  `backend/server.py` includes its router after the API routes.
- `frontend/public/robots.txt` permits public crawling, excludes selected
  authenticated/API paths and points to the sitemap.
- `frontend/src/pages/public/PublicPage.jsx` sets titles, descriptions,
  canonicals and Open Graph metadata in a browser effect. Studio has separate
  server-rendered metadata. This implementation distinction needs baseline
  assessment; it does not establish a live indexing defect.
- `backend/tests/test_seo_files.py` and `test_studio_cms.py` cover crawl rules,
  sitemap/llms content, revalidation and app-route synchronization. They were
  inspected, not executed in discovery or reconciliation.
- Topic QA, screenshot indexes and asset manifests provide existing conventions
  for evidence provenance, responsive checks, laboratory stability and budgets.
  They do not establish field Core Web Vitals or organic outcomes.
- `docs/STUDIO_CMS.md` is the existing CMS/routing runbook. Reuse it; do not build
  another publishing integration or duplicate deployment instructions.

Pinned evidence:
[CMS source](https://github.com/izafar22/voltx/blob/b21e3277f1ac57c315936f34228a1a908bffc759/backend/services/studio_cms.py),
[React metadata](https://github.com/izafar22/voltx/blob/b21e3277f1ac57c315936f34228a1a908bffc759/frontend/src/pages/public/PublicPage.jsx),
[SEO tests](https://github.com/izafar22/voltx/blob/b21e3277f1ac57c315936f34228a1a908bffc759/backend/tests/test_seo_files.py),
[CMS tests](https://github.com/izafar22/voltx/blob/b21e3277f1ac57c315936f34228a1a908bffc759/backend/tests/test_studio_cms.py),
[robots](https://github.com/izafar22/voltx/blob/b21e3277f1ac57c315936f34228a1a908bffc759/frontend/public/robots.txt).

### CI/CD and documentation PR implications

Direct inspection of `.github/workflows/tests.yml` verifies tests run on push and
pull_request, including documentation changes with no path exclusion. Coverage
includes deploy-helper regressions, disposable MongoDB/API backend tests,
frontend tests/build, Playwright and Storybook checks with uploaded evidence.
Staging packaging creates release metadata with SHA, branch, run number and URL.
The staging deployment job requires a **push to `refs/heads/repair-mvp`** and a
successful test job. Pushing this docs branch or opening its PR can trigger CI,
but does not satisfy that staging-deploy condition. Merging into repair-mvp can
trigger staging CD even for documentation-only changes; no merge is authorized.

`frontend-release.yml` builds release artifacts for matching release-branch paths
or manual dispatch, with 14-day artifact retention. `oracle-frontend-deploy.yml`
triggers on release-branch pushes/manual dispatch, builds only for release refs,
and conditions deploy on `RUSHX_AUTO_DEPLOY_ENABLED` with a production environment.
Environment declaration alone does not prove required reviewers are configured.
No workflow was dispatched and no deployment configuration changed here.

`scripts/deploy-staging.py` contains release metadata checks, run-sequence
protection, locking, health checks and rollback handling. `.emergent/cron/`
contains legacy preview cron reconciliation/webhook dispatch scripts; their
activation is unknown and they are not a verified SEO report scheduler.
Temporary CI artifacts are insufficient as the sole long-term evidence archive.

Pinned workflows:
[tests/staging](https://github.com/izafar22/voltx/blob/b21e3277f1ac57c315936f34228a1a908bffc759/.github/workflows/tests.yml),
[artifact build](https://github.com/izafar22/voltx/blob/b21e3277f1ac57c315936f34228a1a908bffc759/.github/workflows/frontend-release.yml),
[production frontend](https://github.com/izafar22/voltx/blob/b21e3277f1ac57c315936f34228a1a908bffc759/.github/workflows/oracle-frontend-deploy.yml).

## 4. Reconciliation: differences and documentation discrepancies

| Area | Original inspection versus approved integration baseline | Consequence |
|---|---|---|
| Entrypoint/core workflow | AGENTS, workflow rules, project overview, code standards are unchanged between the two SHAs. | Original recovery and approval findings remain applicable. |
| Customer acceptance | Original local edits marked acceptance complete; committed integration context still has older IN_PROGRESS/pending customer-profile and Google acceptance wording. Customer spec tasks/validation were not changed between the two committed revisions. | Do not import local edits, mark those tasks complete or claim this branch verified acceptance. |
| Additional workstreams | New privacy/deletion, WhatsApp lifecycle, WhatsApp estimate decisions and repair-workflow transparency specs are present. | Reuse richer multi-workstream precedent; account for public-content/consent dependencies. |
| Registry coverage | Registry adds privacy and lifecycle entries, but does not list estimate decisions or repair-workflow transparency despite their directories. | Registry is a useful index, not a complete inventory. No unrelated registry repair in this change. |
| Public routes/sitemap | CMS SPA allowlist and SITEMAP_STATIC now include `/privacy-policy` and `/data-deletion`; SEO tests assert inclusion. | Original five-page inventory is incomplete. Future audit must include both pages. |
| Path normalization | CMS SPA detection decodes, trims trailing slash and lowercases; React metadata routing similarly normalizes. Tests add case/encoding/trailing-slash coverage. | Reuse current behavior; do not plan fixes from the old revision without retesting. |
| Geography/copy | CMS llms facts, home/how-it-works metadata and footer now target Delhi/NCR. Repair-transparency requirements explicitly restrict this acquisition phase. | Future local SEO must start with that approved scope, not older Mumbai/pan-India claims. Actual business/service facts still require verification. |
| Tracking | `frontend/public/index.html` no longer contains the legacy Emergent runtime loader/PostHog initializer. Privacy spec records owner-approved removal. | Do not presume existing conversion tracking or reintroduce removed tracking implicitly. Analytics availability is unknown. |
| Public presentation/performance | Lifecycle component, content, browser tests, animation/performance follow-ups and canonical brand assets were added. | Audit the current presentation and reuse brand/QA contracts. Do not duplicate lifecycle content. |
| CI | tests.yml adds a synthetic dispatch address; existing trigger/deployment conditions remain unchanged. Other two workflows are unchanged. | Docs push/PR runs CI; only qualifying integration push can deploy staging. |
| Handover/legacy memory | Project handover, memory PRD, CMS runbook, deployment requirements, scripts and Emergent files are unchanged between SHAs. | Their older limitations/conflicts persist; unchanged does not mean current. |

Persistent discrepancies, recorded rather than cleaned up:

1. Architecture/progress still label Growth Studio not deployed, while the
   2026-11-14 handover records operator-reported production cutover. Neither is
   proof of today's release. Current production and staging remain unverified.
2. Deployment requirements retain an earlier incomplete-staging-CD checkpoint;
   workflow code includes staging CD and newer context records historical activation.
3. Architecture describes frontend delivery as proposed/manual; workflow code has
   release-push triggers. Repository environment protection/activation is unknown.
4. Handover says READ FIRST, whereas AGENTS prescribes the six-file order. Use the
   root entrypoint order, then dated handover as supplementary evidence; clarify
   instruction wording only in an approved follow-up.
5. Handover contains older branch counts, release naming and operational claims.
   Newer context also contains dated pre-implementation paragraphs alongside later
   implementation notes. Interpret dates and source rather than flattening them.
6. Current progress refers to review pending for motion work that the base Git
   history already includes through PR #84. Source merge does not prove current
   deployment or acceptance. No unrelated status was altered here.
7. Legacy `memory/PRD.md` and historical `test_result.md` protocol remain present.
   The latter defines testing-agent communication, not the current SEO backlog.

## 5. Existing overlap and unknowns

Verified open PR metadata on 2026-11-28 includes:

- [PR #61](https://github.com/izafar22/voltx/pull/61), architecture memory proposal,
  targets repair-mvp. Its single proposed document defines ADR capture and a
  cold-start check, but explicitly says no capture automation is installed.
  Reviewed at head `11fb7c88d4a9b7ce9cfd4a933b242683a6716316`:
  [proposed workflow](https://github.com/izafar22/voltx/blob/11fb7c88d4a9b7ce9cfd4a933b242683a6716316/docs/ARCHITECTURE_MEMORY_WORKFLOW.md).
  It is not in this integration base and is not an adopted ADR framework.
- [PR #35](https://github.com/izafar22/voltx/pull/35), requirement-confirmation
  gates; [PR #54](https://github.com/izafar22/voltx/pull/54), unified Oracle CI/CD;
  [PR #48](https://github.com/izafar22/voltx/pull/48) and
  [PR #47](https://github.com/izafar22/voltx/pull/47), CD proposals. Titles/base/state
  were inspected, not their full implementation. Do not treat open proposals as policy.
- [PR #85](https://github.com/izafar22/voltx/pull/85), additive lifecycle restoration,
  overlaps the public pages relevant to a future content audit. Its title/base/state
  were inspected; no unmerged changes are incorporated here.
- [PR #71](https://github.com/izafar22/voltx/pull/71) and
  [PR #70](https://github.com/izafar22/voltx/pull/70) concern customer-profile
  production evidence/candidate work. Their existence does not prove deployment.

The open-PR inventory is a dated snapshot, not an exhaustive audit of historical
branches, private work or external marketing systems. Growth Studio, public
privacy and repair transparency are overlapping capabilities, not a complete SEO
workstream. No complete SEO strategy, keyword map, recurring SEO report history,
GSC workflow or organic conversion measurement contract was identified in the
inspected harness. GSC/analytics ownership, access, available data, field metrics,
GBP state, competitors and actual SEO performance are unknown. No website crawl,
external strategy research, analytics query or live release check was performed.

## 6. Proposed SEO architecture and canonical ownership

Reuse the current specification lifecycle. This discovery-only exception to the
usual three-file spec starts with this populated document, as explicitly requested;
requirements/design/tasks are not created as empty placeholders. Later follow
requirements → design → tasks approval, then authorized implementation.

| Information | Proposed canonical location inside `specs/seo-digital-marketing/` |
|---|---|
| Initial discovery, provenance, reconciliation | `discovery.md` (this document) |
| Business/functional scope, outcomes, acceptance, privacy | `requirements.md` |
| Complete SEO master strategy, phases, measurement design, decisions, assumptions and risks | `design.md` |
| Execution backlog, stable SEO-NNN IDs, dependencies, acceptance, status, blockers and next action | `tasks.md` |
| Verification evidence, commands/results, implementation and deployment history | `validation.md` |
| Baseline audit and detailed technical findings | `baseline-audit.md`, `technical-findings.md` |
| Keywords and page mapping | `keyword-research.csv`, `keyword-page-map.csv` |
| Competitors and detailed channel research | `competitor-analysis.md`, `local-seo.md`, `content-strategy.md`, `backlink-strategy.md` |
| Historical nonsensitive performance aggregates | `metrics/`, with definitions/provenance in its README when first needed |
| Weekly/monthly historical reports | `reports/weekly-YYYY-MM-DD.md`, `reports/monthly-YYYY-MM.md` |

Only discovery.md exists now. Supporting research expands named strategy sections
without copying the complete strategy. Research and metrics do not become a second
task tracker. Shared context contains a short link/status only; the existing project
handover supplies a recovery pointer. Operational runbooks remain canonical where
they are. If PR #61 is adopted later, link accepted cross-cutting ADRs rather than
copying decisions into competing registries.

This allocation covers all requested persistence needs: complete strategy and
phases; actionable dependent tasks and acceptance; baseline/technical audit;
keyword research/page mapping; competitor/local/content/backlink strategies;
GSC, website performance, organic traffic and conversion aggregates; historical
weekly/monthly reports; implementation/deployment history; decisions, assumptions,
risks, blockers; verification evidence; current state and next action.
It specifies storage ownership, not invented strategy, data or approved requirements.

## 7. Recovery, checkpoints and verification proposal

### Independent session recovery

1. Establish repository access, branch, exact SHA and local changes; fetch/read
   current remote evidence where appropriate. Do not overwrite another workstream.
2. Read AGENTS and the six context files in order. Discover SEO through the registry
   or progress tracker; read this discovery, then populated approved requirements,
   design, tasks and relevant validation as they become available.
3. Read the latest relevant report, metric definitions and supporting research;
   inspect relevant source/tests and current PRs. Use dated handover as supplementary
   evidence. Verify runtime only when a task needs runtime facts.
4. State task, dependencies, evidence gaps, blockers, authorization boundaries and
   next safe action. Do not confuse merged, implemented, deployed and effective.
5. Codex uses its selected checkout. ChatGPT needs connected repository access or
   a revision-labelled snapshot; attachments may be stale. Neither chat history
   nor a ChatGPT Project copy automatically updates Git.

Current recovery outcome: discovery persisted for review; no SEO requirements or
implementation started. Next proposed task is SEO-000.03 after independent review.

### Session checkpoint

Use existing mechanisms together: tasks records active/completed tasks, blockers,
dependencies and next action; validation records date/revision/method/result and
limitations; reports record period, source, filters and comparison; shared progress
and project handover link to the canonical workstream. Preserve decisions and
approval provenance in design/requirements rather than chat alone. Meaningful PRs
update affected context, per existing rules. No automatic checkpoint service is
proposed.

### Evidence gates

- Findings identify URL/source, observation time, method and limitations.
- Metrics identify reporting window/timezone, filters/dimensions, definitions,
  collection date and freshness. Missing data is unavailable, not zero. Distinguish
  GSC clicks, analytics sessions and conversions; distinguish lab from field data.
- Implementation uses relevant existing tests/regressions, claim/content review and
  diff/privacy checks. Report commands actually run, including failures/not run.
- Release evidence links tested commit/artifact, PR/run, frontend and backend
  revisions separately when relevant, rollout/rollback and verification date.
  Existing explicit merge/production authorization remains mandatory.
- Observed outcome requires a later defined measurement window; shipping alone is
  not SEO success. Keep owner-reported and independently observed evidence distinct.

## 8. Gaps, risks and duplication controls

| Gap/risk | Proposed control |
|---|---|
| No SEO strategy/backlog or measurement contract | Draft/review requirements first; do not fill with fabricated research or metrics. |
| Parallel harness/state/ADR tracker | Keep one spec, existing context/registry/handover; coordinate PR #61 if adopted. |
| Repeated strategy/backlog across docs | Canonical ownership above; shared documents contain links only. |
| Stale local/chat/handover state | Date/SHA/provenance labels; recover from current repository and source evidence. |
| Existing CMS/public content rebuilt | Reuse Studio, metadata, route tests, lifecycle and brand contracts. |
| Privacy/tracking scope drift | Respect removed tracking and existing privacy decisions; new collection requires scoped design/review. |
| Credentials, PII or sensitive analytics in Git | Exclude tokens, raw identifiers, customer-level conversions, sensitive query/URL exports and unredacted screenshots; only approved nonsensitive aggregates. |
| Private evidence unavailable to next agent | Keep safe provenance/reference and access limitations; never claim inaccessible data was verified. |
| Artifact expiry destroys history | Preserve sanitized durable findings/provenance, not just transient artifact URLs. |
| Concurrent workstream writes | Isolated branch/PR, inspect conflicts and preserve unrelated edits. |
| Docs merge causes staging CD | Do not merge in this task or bypass workflow; disclose integration-push trigger. |
| Unsupported local SEO claims | Delhi/NCR acquisition scope from current source; verify business facts, facilities, authorization and service availability before claims. |
| Unknown branch protection/runtime state | Do not infer activation from workflow YAML, branches or historical docs. |

No new credential store, agent framework, scheduler, application module or analytics
integration is proposed by this persistence change. Raw sensitive data should remain
in an approved access-controlled system outside Git; its destination and retention
policy are not selected here. Ignore rules alone are not a privacy review.

## 9. Actual reconciliation verification

Performed on 2026-11-28:

- Read root instructions and all six required context files on both checkouts;
  inspected spec conventions, examples, handover, CMS source/tests/metadata/robots,
  workflow definitions, helper safeguards and relevant comparisons.
- Confirmed repository identity, original branch/HEAD/status and tracked-diff
  fingerprint; fetched repair-mvp; checked requested branch absent locally/remotely;
  created isolated worktree at exact recorded remote SHA and requested branch.
- Inspected Git history/diffs and open PR metadata, plus PR #61 proposed document.
- Validated documentation link targets, pinned baseline file references, changed-file
  allowlist, original-tree preservation and `git diff --check` before committing.
- Reviewed added documentation for secrets, customer PII, sensitive analytics and
  duplicate state systems. No analytics exports or customer records were added.

Application/backend/frontend/browser/deployment regression tests were **not run**:
this change only adds discovery documentation and three references. CI triggered by
push/PR is separate; no CI pass or runtime success is asserted here. No production
or staging configuration, data, messaging, deployment or SEO behavior changed.

## 10. Acceptance conditions, prioritized plan and next action

Independent review remains **CONDITIONAL PASS**, not final acceptance. Conditions
for final discovery acceptance:

1. Reviewer confirms the approved-base reconciliation and material differences.
2. Reviewer verifies canonical persistence and recovery through registry/context/
   handover links, without importing the original local customer-profile edits.
3. Reviewer checks evidence labels, twelve areas, ownership coverage, privacy,
   documentation-only diff, branch ancestry and checks reported in the draft PR.
4. Reviewer assesses open-memory/public-content overlaps and disclosed CI/CD risk.
5. Any required CI/review findings are resolved; merge requires separate owner
   authorization and awareness that integration pushes can deploy staging.

Priority plan preserved from original discovery, refined for this request:

| Priority | Action | Acceptance |
|---|---|---|
| P0 | Reconcile/persist SEO-000 in isolated docs branch | Exact base, differences, provenance, preserved local work and reviewable draft PR (this task). |
| P0 | Independent review | Final discovery acceptance explicitly recorded; no self-issued PASS. |
| P1 | SEO-000.03 — SEO requirements | Draft complete persistence/business scope, metrics/data access/privacy and acceptance; review before design/implementation. |
| P1 | Design/master strategy | Research-backed phases, measurement model, decisions/risks and ownership reviewed; no fabricated findings. |
| P1 | Tasks | Stable IDs, dependencies, acceptance, evidence and next action reviewed before execution. |
| P1 | Measurement/report conventions | Sources, windows, permitted aggregates, unavailable data and external evidence handling defined. |
| P2 | Cold-start walkthrough | Fresh ChatGPT/Codex sessions recover the same state, boundaries and next task from repository access. |
| P2 | Relevant stale-doc reconciliation | Separately scoped, current evidence, no incidental unrelated cleanup. |
| Later | Baseline audit and implementation | Separately scoped/authorized; existing verification and release gates remain. |

Next action: submit this documentation-only draft PR for independent review, then
stop. SEO-000.03 is a recommendation, not authorization to create requirements now.
