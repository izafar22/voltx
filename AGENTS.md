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

## Check the live production release

When asked what is deployed, run this read-only check from the Mac with the dedicated key loaded in its SSH agent:

```sh
ssh -T -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 \
  -i "$HOME/.ssh/rushx_prod_release_check" rushx-release-check@168.138.113.64
```

The restricted account runs the release check when connected without a remote command. Report the frontend SHA from `frontend_release_dir` and the backend SHA from `backend_working_dir` separately. Check that `backend_pid` is nonzero before reporting the backend as running. For each SHA, look for exact matches in local and cached origin release refs:

```sh
git for-each-ref --points-at "$sha" --format='%(refname:short)' \
  'refs/heads/release_*' 'refs/remotes/origin/release_*'
```

Check `git ls-remote --heads origin 'refs/heads/release_*'` for current remote refs if needed. If the branch is ambiguous or unavailable, report the SHA and explain what could be verified. If SSH fails, report the current deployment as unverified and label any historical evidence with its date.

## Check the live staging release

Run this read-only check from the Mac with the dedicated staging key loaded in its SSH agent:

```sh
ssh -T -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 \
  -i "$HOME/.ssh/rushx_staging_release_check" rushx-staging-release-check@137.23.43.117
```

Read the frontend commit from the resolved `frontend_release_dir` when its basename is a SHA. The manifest fingerprint identifies the served assets, which can be identical across commits. For the backend, report the service state from `ActiveState` and `MainPID`. Report a backend revision only when the release path or deployment metadata identifies it. A working directory such as `/opt/rushx-staging/app/backend` alone does not establish a revision. Report missing revision information or an SSH failure explicitly.

Growth Studio blog (server-rendered by FastAPI, Nginx routing, update route): `docs/STUDIO_CMS.md`.
