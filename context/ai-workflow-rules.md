# Mandatory AI coding agent workflow

## Mandatory requirements and technical-plan approvals (supersedes any conflicting guidance below)
Before an AI agent is tasked with implementation, the assistant must restate each user-requested change with expected before/after UI or behavior, what stays unchanged, assumptions, ambiguities and risks. The user must explicitly approve that understanding. Do not silently infer requirements.

After that approval, inspect code and tests and propose the exact affected files, minimal design, acceptance criteria, regression coverage and rollback. Obtain a **separate** technical-plan approval before any implementation. An approval to implement does not authorize merging, deploying, changing environment variables, sending WhatsApp messages or touching production data. If scope changes, stop and reconfirm.

## Current branch policy (supersedes older branch/release examples below)
`repair-mvp` is the protected baseline. Start all feature/fix branches from its latest approved state and use reviewed PRs back to `repair-mvp`. Current production release names are `release_<YYYYMMDD>_version<MAJOR.MINOR.PATCH>`. Do not switch production to `main`, `develop` or an old release naming convention without a separately approved transition.


These rules apply to Codex and other agents working on RushX.

## 1. Preflight (before editing)
- Read root `AGENTS.md` and all six `context/` files.
- Confirm repository, current branch, intended base, open related PRs and working-tree state.
- Inspect actual source, tests and recent changes relevant to the task. Documentation is not evidence that code or deployment exists.
- Identify protected flows (auth, WhatsApp OTP, repair requests, payments, production data), parked feature dependencies, and security risks.
- If task scope or release target is ambiguous, ask before editing.

## 2. Branch discipline
- New feature: `feature/<descriptive-topic>` from the explicitly approved integration base.
- Documentation-only: `docs/<topic>`; urgent fixes: `hotfix/<topic>`.
- `main` is intended to be production-only after a separately approved transition. `repair-mvp` remains the current baseline until that transition is executed.
- Existing `development` and proposed `develop` must not be assumed equivalent.
- Versioned `release_rushx_1.0`-style branches are for release stabilization; approved releases are tagged immutably (e.g. `v1.0.0`).
- Never force-push, delete historical refs, overwrite parked features, merge broad legacy snapshots or retarget CI/Render silently.
- Do not create/rename production or archive branches without approval and an audit of their source commits.

## 3. Implementation
- Make the smallest coherent change. Preserve existing public contracts and working OTP/auth behavior.
- Respect least privilege, consent, PII minimization, validation, idempotency, retries and rollback.
- Never hardcode secrets or write production credentials in docs, code, tests or logs.
- For Meta templates verify live approval, exact name/language and ordered parameters before enabling sends.

## 4. Verification and PR
- Run relevant tests, build, lint/type checks where configured; add regression tests.
- Inspect diff for unrelated changes, secrets, migrations, breaking API changes and missing docs.
- Update applicable context files, especially progress and architecture, within the same PR.
- Open PR with scope, changed files, actual test evidence, risks, rollout and rollback. Do not claim unexecuted tests passed.
- **Never automatically merge or deploy.** Explicit user approval is required for merge, release tagging, deploy, live DB operations, Meta sends or environment changes.

## 5. Release and parked features
- Keep parked code/history reachable; inventory legacy features with branch/commit evidence.
- Restore each approved parked feature on a separate branch with integration tests and migration assessment.
- Stabilize release branch, review, promote to `main`, tag exact deployed commit, verify smoke tests and record rollback SHA.
- No production changes as a side effect of context-documentation tasks.
