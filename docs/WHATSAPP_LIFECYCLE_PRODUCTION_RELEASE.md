# WhatsApp lifecycle production release 1.2.0

Status: candidate preparation. This document is not deployment authorization.

## Scope

The candidate starts at the verified live production frontend and backend revision
`479d2ee1e7337bd3db46a898d7a6ffb53887a994` and selectively includes:

- the consent-based eight-message repair lifecycle and recovery worker;
- the audited Meta Utility template contracts;
- WhatsApp estimate approval/decline actions with compact signed payloads;
- the reviewed merchant payment QR attachment gate; and
- public privacy-policy and data-deletion pages.

Staging-only activation, continuous-delivery and receipt-isolation changes from PRs
#77 and #79 are not part of this release. The shared staging validation module is
retained because lifecycle operator commands import it; it is a no-op unless
`APP_ENV=staging`.

## Production prerequisites

Before activation, an operator must verify without printing secret values:

1. The exact candidate SHA passed the full repository CI and its frontend/backend
   artifacts and checksums were retained.
2. The production WhatsApp sender, WABA webhook callback, verify token, app secret,
   approved template names/languages, and dispatch address are correct.
3. A new production activation UUID and a random estimate-action signing secret are
   configured. Old/staging activation IDs and secrets must not be reused.
4. The reviewed QR is hosted at an HTTPS URL on the production domain and its
   configured URL resolves to that exact asset.
5. Required MongoDB indexes from `services.lifecycle_readiness.INDEX_PLAN` are
   reviewed and installed before the worker starts.
6. The API and separately managed WhatsApp worker are pinned to the same release
   directory and environment file.
7. Backlog inspection confirms activation will not notify historical repairs.

Configuration changes must preserve existing credentials and use the production
environment file. Do not place credentials, customer numbers, dispatch-address
details, or signing secrets in Git or command output.

## Deployment and verification

Deploy only after the owner approves the exact CI-tested SHA. Retain the current
release directories for rollback. Switch frontend and backend to the same candidate,
test Nginx, restart the API, start the pinned worker, and then verify:

- API and frontend health plus policy-page routes;
- backend service state, nonzero PID and exact working directory;
- worker readiness, heartbeat and exact revision;
- webhook verification and one owner-authorized production end-to-end repair;
- no unexpected backlog sends or failed/dead-letter jobs.

The frontend release workflow builds artifacts automatically for release branches,
but production deployment remains disabled while `RUSHX_AUTO_DEPLOY_ENABLED=false`.
The backend and worker require an operator-controlled deployment.

## Risks and rollback

Risks include duplicate notifications, template drift, stale action tokens, a shared
WABA callback moving away from staging, and exposing an incorrect QR or dispatch
address. Pause lifecycle processing first if messaging is unhealthy. Roll back the
frontend and backend to the recorded production baseline together, repin or stop the
worker, and restore the previous callback/configuration as applicable. Additive
notification records may remain; do not delete production data as part of rollback.

## Evidence to record

Record the approved SHA, CI run and artifact checksums, deployed frontend/backend and
worker revisions, configuration/readiness audit (redacted), smoke-test results, and
rollback targets. Update this file and the progress tracker after verification.
