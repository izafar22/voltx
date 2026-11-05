# Parked feature preservation audit

Verified 2026-11-06 using GitHub branch and compare APIs. This is an initial inventory, not an exhaustive code-level feature audit.

## Preserved refs
- `archive/full-product-snapshot` -> `4be0531abd8dec5b7ac12f289b40ef2c867f309f` (original `main` head before production-branch transition).
- `development` -> `2fd5161aa1906d5f5e8c75883e2cef3f4cf43fd9` (historical development).
- `develop` -> initially `a01d2935bba54804647dc64ce8b527e64788cb44` (current repair-focused integration baseline).
- `repair-mvp` -> `a01d2935bba54804647dc64ce8b527e64788cb44` at audit.

## Evidence
- GitHub compare `development...main`: main has two additional commits; changed files include `frontend/src/pages/admin/AdminDashboard.jsx` and `frontend/src/pages/customer/RepairDetail.jsx`. These are potential legacy feature differences, not proof of independent production-ready modules.
- GitHub compare `main...repair-mvp`: repair-mvp is ahead by 18 commits; this is commit ancestry, not a guarantee of functional parity.
- Historical charger/map/wallet/owner flows require per-module inspection and tests before marking them recoverable.
- Keep historical branches intact. Never merge archive wholesale into develop or main.

## Next checks before main transition
1. Verify current Render backend/frontend deploy branches, latest deployed commit, custom domain, and rollback route.
2. Inventory parked features with code paths, commit refs, dependencies, data migrations, auth/security risks and tests.
3. Confirm whether `main` branch protection/default branch changes are needed and whether CI uses branch filters.
4. Prepare and validate a release candidate from `develop`; promote only after explicit approval and smoke tests.
5. Record immutable release tag and actual production deployed SHA.

No production branch was repointed, no Render settings changed and no database operations performed in this audit.
