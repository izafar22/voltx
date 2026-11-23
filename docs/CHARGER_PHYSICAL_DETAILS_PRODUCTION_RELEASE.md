# Charger physical details production release 1.3.0

Status: candidate preparation. This document is not deployment authorization.

## Scope

The candidate starts at the independently verified live production frontend and
backend revision `81e8226d3635a71fd5c078f7c273ea812112d5e3` and selectively
includes PR #81 only.

The customer repair-booking form now requires charger weight in kilograms and
the longest-side length in centimetres. These values are stored with the repair
request and shown in customer and administrator repair details. The API fields
remain optional so existing clients and historical repairs continue to work.

Unrelated commits currently present on `repair-mvp` are excluded. No database
migration, new index, environment variable, provider change, or WhatsApp message
change is required by this release.

## Validation and deployment gate

PR #81 passed repository CI and the exact merge revision was deployed to staging
as both frontend and backend revision
`817827baad308f0759e8a0f1f213f83835937bf8`. The staging backend was active with
a nonzero PID, and the staging release paths identified that exact revision.

The production candidate is a new commit because PR #81 is selectively applied
to the production baseline. Before deployment, the exact candidate SHA must pass
the full repository CI, retain its packaged frontend and backend artifacts, and
receive explicit owner approval by SHA.

Deploy the frontend and backend from the same approved SHA. Preserve the current
production release directories and do not change the existing WhatsApp worker or
production configuration as part of this release.

## Risks and rollback

The principal user-facing risk is preventing a new repair request when either
measurement is missing or outside the accepted range. Compatibility risks include
idempotent retries from older clients and repairs created before these fields
existed; both are covered by optional API fields and regression tests.

If production verification fails, restore both frontend and backend to
`81e8226d3635a71fd5c078f7c273ea812112d5e3`. No data rollback or destructive
operation is required because the new fields are additive.

## Post-deployment verification

Verify the live frontend and backend revisions independently, confirm the backend
is active with a nonzero PID, and smoke-test one owner-authorized repair booking
with valid measurements. Confirm the values appear in customer and administrator
repair details and that an older repair without measurements still loads normally.
