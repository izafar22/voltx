# RushX agent entrypoint

Before making changes, read all six files in `context/`, then inspect the relevant source code, tests, and current Git branch. Treat documentation as guidance, not proof of runtime behavior. If code and context disagree, report the mismatch and update context in the PR.

Required reading order:
1. context/ai-workflow-rules.md
2. context/project-overview.md
3. context/architecture.md
4. context/code-standards.md
5. context/ui-context.md
6. context/progress-tracker.md

Do not merge, deploy, alter Render settings, run production migrations, send production WhatsApp messages, or modify live data without explicit user authorization. Never include secrets or personal customer information in commits. Keep parked functionality preserved and out of releases until separately approved. Every PR must describe tests run, risks, and context documentation changes.

## Mandatory human confirmation gates
For every proposed product, UI, API, integration, or infrastructure change:
1. **Requirements gate:** Restate each requested change in plain English, including before/after behavior, explicit non-goals, preserved functionality, ambiguities and assumptions. Ask targeted clarification questions. **Do not draft a Codex execution task or edit files until the user explicitly confirms this interpretation.**
2. **Technical-plan gate:** After confirmation, inspect the relevant actual code and tests; provide exact proposed scope, impacted files/interfaces, acceptance criteria, regression tests, risks and rollback. **Wait for separate approval before implementation.**
3. **Implementation gate:** Work only on a dedicated branch created from the latest `repair-mvp`; make minimal changes; no unrelated refactors, dependencies or configuration changes. Show the diff and actual test/build results. Submit a PR targeting `repair-mvp`.
4. **Merge gate and deployment gate:** Both require separate, explicit approval. Never assume approval carries forward from an earlier gate.

If a requirement changes during implementation, stop, restate the changed requirement, and repeat the necessary approvals. A passing test is not proof of unchanged UI; perform appropriate visual/manual regression checks and report what could not be verified.

## Current RushX deployment and branch conventions (2026-11-10)
- Protected integration baseline: `repair-mvp`; no direct commits or force-pushes.
- Feature and fix branches originate from `repair-mvp`; reviewed PRs merge into it.
- Production release branches: `release_<YYYYMMDD>_version<MAJOR.MINOR.PATCH>`, created from an approved `repair-mvp` commit. Do not silently switch to `main` or old `release_rushx_*` conventions.
- React frontend remains hosted on Render; FastAPI runs on Oracle Cloud Always Free behind Nginx at `https://api.evchargerrepair.in`; MongoDB Atlas is external.
- Frontend-only text/UI changes must not trigger backend redeployment. Do not modify Render environment, Oracle services, Google OAuth, OTP, WhatsApp, repair lifecycle, API contracts, or live data without explicit scope and approval.
- These deployment facts are last user-verified context, not a substitute for checking the current environment before an operation.
