# RushX Oracle frontend CI/CD — setup and operation

**Status:** Proposed; no production environment, secrets, SSH, or server settings are changed by this PR.

## What changes

The existing `.github/workflows/frontend-release.yml` continues to build release artifacts. A separate, manually dispatched `oracle-frontend-deploy.yml` builds and tests a `release_*` branch, uploads an artifact, waits at the GitHub `production` environment gate, and then sends only the compiled frontend to Oracle. It does **not** deploy on merge or push. The run's exact commit SHA identifies the release.

## Mandatory one-time setup (requires separate authorization)

1. In GitHub repository **Settings → Environments**, create `production`, configure **required reviewers**, enable **prevent self-review** if available, and restrict deployment branches to `release_*`. Check that the repository plan supports enforcement of environment required reviewers. **Do not run this workflow if the approval gate cannot be enforced.**
2. Only after verifying the required-reviewer protection, set environment variable `APPROVAL_GATE_CONFIGURED=true`. This flag is an operator assertion, not independent verification of the GitHub environment rules.
3. Set environment variables `ORACLE_HOST` (verified current Oracle IP or DNS) and `ORACLE_USER` (SSH deploy account). Set environment secrets `ORACLE_DEPLOY_SSH_KEY` (dedicated private key) and `ORACLE_SSH_KNOWN_HOSTS` (out-of-band verified host key line). Do **not** generate host trust dynamically with `ssh-keyscan` during deployment or store keys in git.
4. Create a dedicated non-root SSH deployment account/key. Give that account write permission **only** to the frontend webroot, release and backup directories, and its home deployment staging directory. The deployed SHA marker is written at `$HOME/rushx-deploy/frontend-deployed-sha` rather than the protected `/var/www/rushx` parent. Ensure Nginx can read deployed files. Do not grant passwordless sudo. Review the account permissions and the server directory ownership before enabling deployment.
5. On the VM, verify `rsync`, `setsid` (util-linux), `python3`, `tar`, `flock`, `nginx` and `curl`; validate free disk space for at least one release plus a full backup. Check `/var/www/rushx/frontend` is a real directory and not a symlink, and verify live Nginx root and site configuration.
6. Reconcile the current deployed SHA, TLS, DNS, API health, and Nginx config with `docs/ORACLE_PRODUCTION_DEPLOYMENT.md` before first deployment.

## Manual release

1. Merge approved frontend changes to `repair-mvp` via reviewed PRs.
2. Prepare a versioned `release_YYYYMMDD_versionX.Y.Z` branch from the approved commit (per existing RushX release policy).
3. In Actions, select **Deploy RushX frontend to Oracle**, choose the release branch, then **Run workflow**.
4. Review tests and build output. An authorized reviewer approves the `production` environment job only after reviewing the commit and artifact. Deployment fails closed when `APPROVAL_GATE_CONFIGURED` is not `true`.
5. Verify public homepage, theme, mobile layout, JS/CSS, click-to-chat, and protected API routing. Browser-based E2E and contrast checks are still needed before routine use; the workflow's smoke check does not replace them.

## Rollback

The deployment script stages the artifact at `/var/www/rushx/releases/<sha>`, backs up the current live webroot under `/var/www/rushx/backups/frontend-<UTC timestamp>`, and uses `rsync` to update `/var/www/rushx/frontend`. If an in-script verification fails, the trap restores the backup. The remote deployment script now checks the public HTTPS homepage before disarming its rollback trap; failure or an INT/TERM/HUP interruption at this stage attempts automatic restore. The rollback launches `rsync` in a separate process group using `setsid -w` and ignores repeated signals in the parent shell. The public HTTPS response is stored in a unique temporary file and cleaned up on exit. The GitHub job independently checks the public website afterward. **A later GitHub-runner smoke-test failure or a post-deployment regression does not automatically roll back**; retain the backup for an operator-approved recovery.

The current live webroot is a directory, so the `rsync` update is **not atomic**. A versioned symlink release layout would require a separately approved Nginx/webroot migration. Do not claim zero downtime.

## Review checklist before activation

- [ ] Verify GitHub environment required reviewers are enforced for this repository and cannot be bypassed by a workflow author.
- [ ] Verify the dedicated non-root SSH account has only the required filesystem permissions.
- [ ] Run YAML validation, shell syntax/static checks and a staging deployment/rollback rehearsal.
- [ ] Confirm a failed public HTTPS check restores the previous frontend.
- [ ] Verify the existing Nginx document root and concurrent requests during the rsync update.
- [ ] Verify protected API routing, both themes, and mobile layout.

## Scope and risks

- Frontend only; no backend, database, WhatsApp outbox, DNS, TLS, or Nginx edits.
- CI deploy access and GitHub environment approvals must be configured and tested independently.
- The non-root deploy account needs carefully scoped filesystem permissions; this is a prerequisite for activation.
- Unit tests and build run on GitHub; full browser/axe tests are not integrated in this workflow.
- Existing frontend release workflow remains untouched; this is an additive proposal.
