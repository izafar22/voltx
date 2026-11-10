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

Production deployment reference (operator-verified 2026-11-10): read `docs/ORACLE_PRODUCTION_DEPLOYMENT.md` before changing hosting, Nginx, DNS, TLS, frontend release artifacts, backend routing, or deployment automation. Treat it as a dated snapshot; verify live state.
