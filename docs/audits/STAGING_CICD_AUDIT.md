# RushX staging CI/CD audit

**2026-11-13 · BLOCKED.** [PR #54](https://github.com/izafar22/voltx/pull/54) is open. No staging deployment has been authorized or performed.

## Current state

| Check | Status | Evidence |
|---|---|---|
| Baseline CI | Verified | `repair-mvp` at `8de6d0b` contains Tests, Frontend release artifact, and Deploy RushX frontend to Oracle. [Baseline push CI](https://github.com/izafar22/voltx/actions/runs/43449723832) passed. The latter two workflows build legacy frontend artifacts. The Oracle deploy job is release-branch scoped. |
| PR-only workflows | Verified | PR #54 adds the reusable staging workflow and manually dispatched unified production workflow. At intake GitHub reported the PR open, mergeable and clean. Tests and CodeRabbit passed on `b733b97`. Staging was skipped on the PR as designed. [Intake CI](https://github.com/izafar22/voltx/actions/runs/43458889084) |
| Exact artifact and freshness | Verified in code and CI | Staging depends on the successful Tests job, downloads its named immutable artifact from the same run and validates the branch's current head and archive digest before SSH. Host verification covers both component markers and monotonic CI sequence. A head change after the API check can allow an in-flight older release to finish, but the host lock and sequence prevent it from overwriting an already deployed newer release. A superseded job may fail or be replaced in the Actions queue. |
| Permissions and overlap | Verified in code | Staging uses contents read, an environment-specific SSH key and a staging concurrency group. Production uses a separate group shared with legacy production. Its dispatch guard and environment prevent a staging push from invoking it. The host rejects a deployment targeting the other configured environment. |
| Draft alternatives | Verified | [#47](https://github.com/izafar22/voltx/pull/47) edits the legacy production frontend workflow. [#48](https://github.com/izafar22/voltx/pull/48) adds a separate quality workflow and manual staging scaffold. Both remain open drafts. Continue with #54. |
| Branch protection | Missing | Branch API returned `protected: false`, protection endpoint returned 404, and applicable branch rules were empty. The proposed SSH step fails closed. |
| Staging environment and enable flag | Missing | Only `production` was listed. The staging environment endpoint returned 404. `RUSHX_STAGING_CD_ENABLED` was absent and evaluates as disabled. The authenticated account reports admin access on this public repo. No GitHub settings changed. |
| Public staging | Verified | DNS resolved to a distinct address from the dated production snapshot. TLS verified. `/` returned 200 HTML and `/api/` returned 200 JSON. `/api/health/ready` returned 404 JSON and `/rushx-release.txt` returned HTML via fallback. A successful status alone is insufficient for release verification. |
| VM inventory and rollback baseline | Not verified | Strict host-key checking reached the staging SSH endpoint, which rejected the available login key. Host layout, active build/checkout SHA, interpreter, units, environment file, backups and deployment method remain unknown. |
| Production | Verified repository isolation | Existing production environment and workflows were read for comparison. No production host, database, credentials or settings were accessed or changed during this audit. |

## Security validation

| Control | Result |
|---|---|
| Runtime staging identity, dedicated Atlas host/user/database, no demo OTP, staging-only CORS, WhatsApp allowlist and repair notification guards | Source and offline tests pass. Effective VM values and actual Atlas roles/network isolation are unverified. Treat any shared or broad identity as a blocker. |
| Google staging origin/callback and HTTPS cookies | Mocked callback, state rejection and session tests pass. Live staging OAuth client registration and identity smoke are unverified. |
| Secret handling | Package explicitly selects tracked runtime files, validates extraction, and omits backend dotenv. The workflow sources distinct named SSH credentials and pins. Provisioning, key restrictions, secret file access and ownership of the live preflight are unverified. |
| GitHub branch gate and deployment environment branch policy | Branch guard implemented. Live enforcement and staging environment branch policy are missing. |

## Gaps and recovery

| Classification | Root cause and required change | Risk, verification and rollback |
|---|---|---|
| Security blocker | Protect `repair-mvp` using a branch protection rule and require the actual Tests job check. Create `staging` with only the `repair-mvp` branch allowed. | Without protection the workflow refuses SSH. Verify the API and a normal PR flow. Keep the flag false while adjusting settings. |
| Implemented but not configured | Add `RUSHX_STAGING_ORACLE_HOST`, `RUSHX_STAGING_ORACLE_USER`, `RUSHX_STAGING_ORACLE_SSH_KEY` and `RUSHX_STAGING_ORACLE_KNOWN_HOSTS` to staging only. Set the repository flag to false during setup. | Verify pins independently and compare the staging deployment public key fingerprint with the separately recorded production fingerprint. Revoke only the staging key if setup is rolled back. |
| Operational blocker | Obtain the VM inventory below, compare to [the runbook](../ORACLE_CICD.md), and verify the current frontend/backend pair and restore path. | Host changes could interrupt working staging. Preserve TLS, backend listener and any Studio routing. Test the restore on an isolated clone before requesting live maintenance. |
| Security blocker | Review effective runtime settings, Atlas role scopes and network access in staging. Confirm the preflight, restricted SSH account and server-side secret handling. | A shared credential or unrestricted identity blocks activation. Keep deployment disabled and resolve staging privileges in a separately approved change. |
| Implemented but not tested on the host | Activate only after reviewed VM readiness and authorized staging rollout. | Rehearse dependency install, Nginx/API checks, service restart, failure and restoration on a disposable VM matching staging. Restore the previous complete pair if live verification fails. |
| Missing regression evidence at intake | Exercise command failures, DB readiness, wrong SHA/environment, missing artifact, invalid SSH destination, same-commit repeats and interrupted recovery in isolated tests. | Keep this coverage in PR #54 and require green CI. No infrastructure rollback applies to test-only changes. |

## Operator inventory · read-only

Run on the verified staging VM with an authorized operator identity. Substitute confirmed paths and names after discovery. Retain detailed output privately and share only sanitized findings. Avoid `systemctl cat`, process command lines, environment dumps, raw Nginx configuration and raw authorized-key files in shared output.

```sh
hostname
. /etc/os-release; printf '%s\n' "$PRETTY_NAME"
uname -m
getconf GNU_LIBC_VERSION
free -h
df -hT
python3 --version
python3.12 --version
systemctl list-units --type=service --state=running --no-pager
sudo ss -ltnp
sudo nginx -t
sudo nginx -T 2>/dev/null | awk '
  $1 ~ /^(server_name|listen|location|root|alias|try_files)$/ { print }
  $1 == "proxy_pass" {
    if ($2 ~ /^https?:\/\/[A-Za-z0-9.:-]+\/?;$/) print
    else print "proxy_pass [review target privately]"
  }'
systemctl show VERIFIED_FASTAPI.service \
  -p User -p Group -p FragmentPath -p DropInPaths -p WorkingDirectory -p EnvironmentFiles -p MainPID
sudo readlink -f /proc/VERIFIED_MAIN_PID/exe
sudo readlink -f /proc/VERIFIED_MAIN_PID/cwd
git -C VERIFIED_CHECKOUT rev-parse HEAD
git -C VERIFIED_CHECKOUT status --short
sudo stat -c '%A %U:%G %n' VERIFIED_ENV_FILE VERIFIED_WEBROOT VERIFIED_RELEASE_ROOT
sudo find VERIFIED_RELEASE_ROOT -maxdepth 2 -type l -printf '%p -> %l\n'
sudo sha256sum VERIFIED_WEBROOT/index.html VERIFIED_WEBROOT/asset-manifest.json
id VERIFIED_DEPLOY_ACCOUNT
sudo -l -U VERIFIED_DEPLOY_ACCOUNT
sudo sshd -T -C user=VERIFIED_DEPLOY_ACCOUNT,host=staging.evchargerrepair.in,addr=VERIFIED_SOURCE_IP |
  awk '$1 ~ /^(authorizedkeysfile|authenticationmethods|passwordauthentication|permittty|allowtcpforwarding|forcecommand)$/'
sudo ssh-keygen -lf VERIFIED_AUTHORIZED_KEYS
sudo awk '{print "restrict=" ($0 ~ /(^|,)restrict(,| )/) ", forced_command=" ($0 ~ /(^|,)command="/)}' VERIFIED_AUTHORIZED_KEYS
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
for path in /api/ /api/health/ready; do
  curl --max-time 8 -sS -o /dev/null -w '%{http_code} %{content_type}\n' "http://127.0.0.1:VERIFIED_PORT$path"
done
```

The operator should inspect the exact service interpreter and flags privately and classify the actual deployment method using the running process, release symlinks, Git metadata and artifact hashes. Record backup location and a tested restoration procedure for the current pair. Confirm Nginx preserves the API prefix and existing site/TLS behavior. Verify host ABI against the packaged Linux x86-64 Python 3.12 wheels and measure free space with both releases retained.

For runtime safety, have the operator review only the FastAPI service's effective configuration locally and share pass/fail for each control in the table. Use the existing offline staging validator and the reviewed release preflight with the same service environment. Check the Atlas staging project's Database Access and Network Access metadata for a staging-only principal and scoped roles. If authorized, verify ping or connection status only against the approved staging destination. Use staging provider-console metadata to verify OAuth origins and callback, dedicated Meta sender and template, and allowlist ownership. Do not inspect production databases, send OTPs, or print runtime configuration.

## Activation sequence

1. Review the inventory and scope any host changes separately. Verify known-good backup and isolated restoration first.
2. In GitHub Settings, protect `repair-mvp`, require reviewed changes and the Tests check, and disallow force pushes and deletion. Verify `.protected == true`. Create the staging environment, select **Selected branches and tags**, and add only the branch `repair-mvp`. Keep the activation flag false.
3. After approved staging provisioning, configure the four staging environment entries above. Verify the pin out of band, the forced command and two exact allowed service operations. Rehearse package compatibility, failure and rollback on an isolated VM.
4. Obtain explicit approval for merge and staging activation. Once merged, with the flag enabled under that approval, run the current canonical baseline push workflow or rerun all jobs on its still-current successful push. Verify both SHA markers, readiness and staging-only API behavior. Disable the flag and follow the runbook recovery procedure if needed. Schedule separate, authorized Google and WhatsApp tests.
