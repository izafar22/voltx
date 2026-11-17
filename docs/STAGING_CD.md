# Automatic staging deployment

The `deploy-staging` job in `.github/workflows/tests.yml` follows the successful `test` job for pushes to `repair-mvp`. It deploys both components from that run's artifact. PR CI runs do not deploy.

## One-time installation

An administrator on `rushx-staging-vnic` must inspect the existing `rushx-staging.service` user, environment files and Python runtime before installation. The helper requires Python 3.12 and its venv module. Preserve the existing service and environment configuration for rollback.

Create a dedicated Ed25519 deployment key on the operator's Mac. Install its public key using a reviewed checkout of this branch on the staging VM:

```sh
sudo bash scripts/install-staging-cd.sh /path/to/staging-deploy.pub
```

Set GitHub staging environment secrets `STAGING_DEPLOY_SSH_KEY` and `STAGING_SSH_KNOWN_HOSTS`. The first contains the dedicated private deployment key. The second contains the staging host key verified against the VM's host-key fingerprint. Restrict the environment to `repair-mvp`; its deployment job runs automatically without per-run approval.

The installed deployment key invokes a forced dispatcher. Its account can call the staging helper through sudo. The helper is root-owned, validates the staging hostname, serializes releases, rejects unsafe archives and uses the backend's existing non-root service user to install dependencies. Environment secrets remain on staging. A final environment file forces `APP_ENV=staging`, so backend startup runs the existing staging isolation validator.

## Release and failure handling

CI packages the tested frontend build, backend source, resolved Python dependency versions and source/run metadata. The VM creates a separate virtual environment per release, updates a service drop-in for `rushx-staging.service`, and switches the frontend symlink. It verifies the local API, public staging API, homepage and served release metadata. Failure during the switch restores the previous frontend link and service drop-in, restarts the backend and verifies recovery.

The deployment lock and monotonically increasing CI run number prevent an older candidate from replacing a newer successful deployment. A failed attempt retains its directory for diagnosis. A retry replaces that directory after checking that neither component is using it. Cleanup before and after deployment retains the latest five attempts and protects active and previous component releases.

Backend restart creates a short interruption. Frontend and backend switches occur sequentially. Keep changes compatible during that transition. Rollback restores application revisions and configuration selection; database writes or index changes are outside application rollback.

Active metadata is stored at `/opt/rushx-staging/cd/active.json`. The public `/release.json` identifies the served frontend revision. The read-only SSH check resolves the SHA-bearing frontend directory and reports the SHA-bearing backend working directory after the first successful deployment.

GitHub job failures and the workflow summary report the deployment outcome. Enable GitHub Actions notifications for the desired operator recipients. A rollback failure emits a critical message requiring staging operator intervention.

## Verification before recording activation

- Run `python3 scripts/test-staging-deploy.py` and shell syntax checks.
- Verify extraction rejection, older-candidate rejection and recovery from a failed candidate.
- Run the installed helper against the first passing mainline CI artifact.
- Verify both active SHAs using the staging read-only SSH command in `AGENTS.md`.
- Rehearse a failed release on the staging VM and verify both previous revisions are restored.

Implementation and live activation are separate checkpoints. Record the successful GitHub deployment run and any outstanding live checks in `context/progress-tracker.md`.
