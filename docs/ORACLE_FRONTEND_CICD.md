# RushX automatic frontend release deployment (not activated)

**Status: code prepared only. No production deployment or server migration has been performed.**

## Trigger and safety gate
Pushes to `release_*` branches trigger build, frontend tests, and isolated rollback regression tests. The deploy job runs **only when repository variable `RUSHX_AUTO_DEPLOY_ENABLED` is exactly `true`**; leave it unset or false until production readiness is verified. This is an automatic deployment policy, not a manual-review policy. GitHub environment `production` must have no required-reviewer gate if unattended deployment is desired. The existing release process and branch naming remain unchanged.

## Mandatory one-time server migration — separate approval required
The old live path `/var/www/rushx/frontend` is a real directory. The new deploy script **refuses to run** until it is converted to a symlink pointing to an existing, healthy release within `/var/www/rushx/releases/`. This migration must be scheduled and tested separately. Preserve the old frontend as the initial stable release, validate Nginx root resolution, symlink traversal, permissions, TLS, disk space, and rollback before activation. Do not perform this migration from CI or automatically.

Use a dedicated non-root SSH deployment account with write access only to the frontend release directories and its own `$HOME/rushx-deploy` folder. Configure environment secrets `ORACLE_DEPLOY_SSH_KEY`, `ORACLE_SSH_KNOWN_HOSTS`, and environment variables `ORACLE_HOST`, `ORACLE_USER`. Verify the SSH host key out of band. Optional webhook notification secret: `RUSHX_DEPLOY_NOTIFICATION_WEBHOOK` (a JSON webhook accepting a `text` field, such as Slack-compatible). GitHub Actions results and job summaries remain available without a webhook.

## Deployment and rollback
The workflow packages the exact built SHA. On the VM, the script takes an exclusive lock, validates the tarball, extracts to `releases/<SHA>`, and checks JS/CSS. It atomically replaces the `frontend` symlink with `mv -T` and performs local HTTP and public HTTPS smoke checks. On failure it switches the symlink back to the previous healthy release and removes failed staging. It never deletes the currently active release. The deployed SHA marker is stored in `$HOME/rushx-deploy/frontend-deployed-sha`. A failed rollback is logged as critical and requires intervention.

The workflow reports deployment status in its GitHub Actions job summary and optionally POSTs a result to the configured webhook. A runner failure after the remote script completes is **not automatically rolled back**. The checks establish homepage reachability, not complete application correctness; a post-deployment synthetic check, API-route test, and alerting are still recommended. Automatic rollback cannot protect against VM failure, broken DNS, incompatible backend/database changes, or regressions discovered later.

## Activation checklist
- [ ] GitHub CI and CodeRabbit checks pass; validate workflow YAML and shell syntax
- [ ] Test failed deployment, rollback, successful retry, invalid archive, and signal handling in staging
- [ ] Rehearse a symlink migration from the existing live directory, with a recovery procedure
- [ ] Verify Nginx symlink resolution, permissions, TLS, and API routing
- [ ] Configure production SSH credentials, deployment account, and optional webhook
- [ ] Verify release branch protections and expected behavior on branch creation/update
- [ ] Set `RUSHX_AUTO_DEPLOY_ENABLED=true` **only after explicit authorization to activate**


## Restricted privileged helper installation (not performed)

The deploy account does not have general sudo rights and must not own the webroot parent. The root-owned helper source is \`scripts/rushx-release-switch.sh\`. **Review and install only after CI validation and a local rehearsal**:

\`\`\`bash
sudo install -o root -g root -m 0755 scripts/rushx-release-switch.sh /usr/local/sbin/rushx-release-switch
sudo visudo -f /etc/sudoers.d/rushx-release-switch
\`\`\`

The sudoers file should contain exactly:

\`\`\`text
rushx-deploy ALL=(root) NOPASSWD: /usr/local/sbin/rushx-release-switch *
\`\`\`

Then verify with \`sudo visudo -cf /etc/sudoers.d/rushx-release-switch\` and \`sudo -l -U rushx-deploy\`. This grants a narrowly scoped helper command, **not unrestricted sudo**. The helper validates its action and release ID and refuses to remove the active release or protected \`initial-stable\`. The root-owned helper is an additional trusted component; review it carefully and avoid granting the deploy account permission to edit it.

**Migration remains a separate, manual maintenance operation.** Preserve the existing real frontend directory, create and verify \`initial-stable\`, then atomically replace the real directory with a symlink only under a rehearsed maintenance plan. Do not perform this migration using the CI workflow. The initial-stable directory should remain root/ubuntu-owned and non-writable by the deploy user. The helper switches only symlinks and will refuse to act before migration.
