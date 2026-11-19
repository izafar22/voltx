# Customer profile production candidate

Prepared 2026-11-19. This records a candidate, not a completed deployment.

## Scope and baseline

Owner requested production release of the accepted customer-profile spec. Selectively apply PR #69 (`5206722af8a939d903946f0bdef5dfea51104bf1`) to live frontend baseline `1e5da33843cbbdc0a869c9fd691b343661245c15` (local release 1.0.7; no matching remote release ref at preparation). Its backend tree exactly matches running production backend `144e1236f93b6dac1cc74aa8ce86403239f5ad1a` (release 1.0.3). Read-only production SSH verified both paths and nonzero backend PID on 2026-11-19.

Includes customer profile, saved addresses, verified Google/WhatsApp linking and phone replacement, session revocation, repair address snapshots and related tests. Excludes staging safety/provider configuration and staging CD changes. Preserves the currently deployed frontend and backend behavior outside this feature.

## Evidence and remaining gate

Staging acceptance is complete, including owner-confirmed mobile replacement/session revocation and fresh Google sign-in. See `../specs/customer-profile/validation.md`. These results apply to staging commit 5206722; the selected production combination requires its own CI.

Production frontend deployment variable remains false. No verified backend deployment workflow exists. Do not enable automation as a side effect of this release. The historical deployment docs also describe the frontend symlink migration as pending, while the live restricted check resolves a versioned frontend release; inspect actual configuration before cutover.

Before production cutover: require passing candidate backend/frontend/browser/Storybook checks, identify the exact frontend artifact and backend revision, prepare and verify paired rollback, and obtain owner approval of that exact combination under `DEPLOYMENT_REQUIREMENTS.md`. Use an authorized operator path to inspect the current systemd configuration, Python environment, Nginx and protected environment settings without exposing secrets.

## Risks and rollback

Authentication changes include OTP purpose separation and account session epochs; check the existing unique phone and Google-subject indexes through an approved read-only operational check. No new environment variables, secondary indexes, migrations, or OAuth callback destinations are required by this feature. Do not modify existing customer data or send production test WhatsApp messages as part of preparation.

Retain frontend 1e5da338 and backend 144e1236 and their runtime configuration as the paired rollback targets. Rollback preserves additive profile documents and repair snapshots, but older code will not display them. Phone replacements remain account identity changes and older code may require sign-in again. Allow outstanding linking challenges to expire for ten minutes before an ordinary rollback to the earlier auth implementation, or use a separately authorized invalidation runbook. Do not delete profile data during rollback.

## Validation

Candidate CI results are recorded in the pull request. Preparation verified identical backend baseline trees and clean patch whitespace. No new production writes or cutover were performed.
