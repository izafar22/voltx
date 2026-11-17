# Deployment requirements

Agreed with the owner on 2026-11-18. This specification defines the intended deployment behavior. Implementation and activation must be verified independently.

## Source and environment policy

- `repair-mvp` is the integration source of truth.
- Staging must reflect all changes integrated into `repair-mvp` after CI and deployment verification pass.
- Production releases include the features or commits the owner explicitly selects from `repair-mvp`, building on the currently deployed production baseline. Assess dependencies before applying selected changes.
- Production release branches follow `release_<YYYYMMDD>_Version<Major.minor.patch>`. Existing branches use lowercase `version`.

## Automatic staging CI and CD

1. Every push to `repair-mvp`, including a merged PR, automatically runs CI against the exact commit SHA.
2. CI covers backend tests, frontend tests and build, and the applicable existing browser checks.
3. Passing CI automatically triggers staging deployment of the tested frontend artifact and backend revision, without a separate per-deployment approval.
4. Staging uses its dedicated configuration, credentials and data, preserving the existing staging safety checks.
5. Deployment verifies the frontend and backend through health and smoke checks before recording success.
6. A CI failure leaves the active staging release in place. A failed deployment restores the previous working release and reports the failure. A failed rollback requires an actionable notification.
7. Deployment records identify the active frontend and backend SHAs, source branch, workflow run and previous release. The read-only staging lookup must expose both active revisions.
8. Concurrent runs must preserve consistent releases and prevent an older candidate from replacing a newer successful deployment. Once runs settle, staging must reflect the latest successfully tested and deployed `repair-mvp` candidate.

## Selected production releases

1. The owner selects the production features or commits and approves the release scope.
2. Prepare the release from the active production baseline, accounting for the separately deployed frontend and backend revisions.
3. Test the selected release combination through CI before deployment. Staging tests of the full integration branch do not establish that a selected production subset passes.
4. Production deployment requires explicit owner approval of the release. Creating or updating a release branch alone must not authorize deployment. Deploy the exact frontend artifact and backend revision that passed CI and received approval. A change to either requires new CI and owner approval.
5. Verify the deployed frontend and backend, record both active revisions, retain previous releases and provide rollback.

## Acceptance criteria

- A passing `repair-mvp` update reaches staging automatically, with both active SHAs verifiable.
- A failing CI run keeps the existing staging release active.
- A failed deployment demonstrates recovery to the previous working release and reports its outcome.
- Concurrent candidates finish with a consistent, current staging release.
- A production candidate contains the approved selection and passes CI.
- Production promotion requires explicit owner approval.

## Implementation checkpoint

The repository currently contains CI in `.github/workflows/tests.yml` and a production frontend deployment workflow in `.github/workflows/oracle-frontend-deploy.yml`. The earlier audit found staging CD incomplete, production frontend CD disabled, and backend CD missing. Recheck workflows and environment settings before implementation or activation.

Use the read-only commands in `AGENTS.md` to inspect live revisions.
