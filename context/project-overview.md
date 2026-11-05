# RushX project overview

**Product:** RushX, at evchargerrepair.in. **Repository:** izafar22/voltx (historical repository name). **Purpose:** independent, multi-brand EV charger repair enquiries, assessment and repair coordination. Explain feasibility without promising repair success, manufacturer authorization, or unsupported geographical coverage.

## Active repair-focused scope
- Public educational pages and repair enquiry journey.
- Repair request creation, lifecycle management and customer authentication.
- FastAPI backend, React frontend, MongoDB persistence.
- WhatsApp OTP and consent-based lifecycle messaging integration, subject to configuration and template approval.
- Operator/admin functionality where implemented and authorized.

## Parked / deferred features
The broader product history contains functionality outside the repair-focused MVP (historically including charging-station map, charger/wallet/owner-related flows). **Do not assume this is an exhaustive inventory.** Audit `development`, `main`, relevant historic branches and commits before documenting precise locations. Preserve existing refs and commits. Restore only approved features in independent branches, with dependencies and migrations reviewed. Never merge the full legacy application wholesale.

## Branch and release policy
- `main`: intended long-term production source of truth; **transition not yet verified or executed**.
- `repair-mvp`: current repair-focused baseline; do not silently replace or delete.
- `development`: existing branch; audit before choosing/renaming an integration baseline.
- `develop`: proposed integration branch, **not confirmed created**.
- `feature/<topic>`: isolated feature work; `hotfix/<topic>`: emergency fix.
- `release_rushx_1.0` and later versioned branches: proposed release stabilization branches.
- Immutable `v1.0.0`-style tags identify deployed commits. Production deploys should be traceable to a tested tagged commit from `main`.
- No production branch/Render switch until an approved transition plan verifies deployed SHA, rollback, and parked-feature preservation.

## Product integrity
Customer communications must describe actual events; use qualified estimates and verified dispatch details. Never imply images depict actual RushX staff or facilities without verified provenance.
