# Customer profile production release

Deployed and independently verified 2026-11-19. Both components run `479d2ee1e7337bd3db46a898d7a6ffb53887a994` on `release_20261119_version1.1.0`.

## Scope and baseline

Owner requested production release of the accepted customer-profile spec. Selectively apply PR #69 (`5206722af8a939d903946f0bdef5dfea51104bf1`) to live frontend baseline `1e5da33843cbbdc0a869c9fd691b343661245c15` (release 1.0.7; exact historical ref restored on origin with owner approval). Its backend tree exactly matches running production backend `144e1236f93b6dac1cc74aa8ce86403239f5ad1a` (release 1.0.3). Read-only production SSH verified both paths and nonzero backend PID on 2026-11-19.

Includes customer profile, saved addresses, verified Google/WhatsApp linking and phone replacement, session revocation, repair address snapshots and related tests. Excludes staging safety/provider configuration and staging CD changes. Preserves the currently deployed frontend and backend behavior outside this feature.

## Evidence and remaining gate

Staging acceptance is complete, including owner-confirmed mobile replacement/session revocation and fresh Google sign-in. See `../specs/customer-profile/validation.md`. Staging results apply to commit 5206722. The selected production combination separately passed exact-head CI run 44462064627, PR CI run 44462083327 and release-branch CI run 44464527144.

Production frontend deployment variable remains false. No verified backend deployment workflow exists. Do not enable automation as a side effect of this release. Historical deployment docs describe the frontend symlink migration as pending; operator inspection verified that the live frontend already uses a versioned release symlink. No migration was needed.

Owner requested promotion, approved release-branch preparation and the PR, and supplied operator access. Cutover preserved `/etc/rushx/backend.env`, Nginx, DNS and TLS. The release-specific backend runtime uses existing dependency versions; the new `zz-release-1.1.0.conf` drop-in selects the new working directory and Uvicorn executable. Both previous release directories and the old drop-in remain intact.

## Risks and rollback

Authentication changes include OTP purpose separation and account session epochs; check the existing unique phone and Google-subject indexes through an approved read-only operational check. No new environment variables, secondary indexes, migrations, or OAuth callback destinations are required by this feature. Do not modify existing customer data or send production test WhatsApp messages as part of preparation.

Retain frontend 1e5da338 and backend 144e1236 and their runtime configuration as the paired rollback targets. Rollback preserves additive profile documents and repair snapshots, but older code will not display them. Phone replacements remain account identity changes and older code may require sign-in again. Allow outstanding linking challenges to expire for ten minutes before an ordinary rollback to the earlier auth implementation, or use a separately authorized invalidation runbook. Do not delete profile data during rollback.

## Validation

CI results are recorded in PR #70. Exact-head CI: 377 backend tests passed (2 skipped), 187 frontend tests, 116 app browser checks and 151 Storybook checks, plus builds and deploy regression checks.

Tested artifact ID: `14500731562`, from run `44462064627`. Frontend archive SHA256: `3163a7ff598df3ff74d72288aade2b332586b6e7c15c108af021139b8cdef9b2`. Backend archive SHA256: `9697c5e44bc340b1635c4558f6ecfff4d312cf872313e91093e0c481f8ef18d1`. Checksums were verified locally and on the VM.

Runtime preflight passed package consistency, application import and read-only index/phone-normalization audits. After cutover, independent SSH confirmed both release paths at 479d2ee and backend PID 77921 (a point-in-time observation). Public HTTPS homepage/profile route/API checks passed; unauthenticated profile access returns 401; OpenAPI exposes the profile route; manifest and main JS/CSS match the staged files byte for byte. No authenticated production data-write or provider-send checks were run.

Protected backup: `/var/backups/rushx/customer-profile-20261119T055839Z`, containing the previous service configuration, protected environment backup, Nginx snapshot, frontend archive, revision records and root-only `rollback.sh`. No secrets were copied to Git. This is a code/config backup, not a database backup. Rollback was prepared, not exercised on production.

PR #70 is a review record against the historical 1.0.7 baseline; deployment came from the new release branch without merging into or advancing the historical baseline.
