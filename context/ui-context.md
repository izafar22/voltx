# RushX UI context

## Existing implementation
React 18 frontend under `frontend/`, React Router, shared public-storytelling components under `frontend/src/pages/public/storytelling/`. Inspect existing CSS and components before making design decisions.

## Visual direction
Preserve RushX identity, editorial typography, green accent and light/dark theme behavior already present in the app. Homepage headline: **Repair when possible. Replace when necessary.** Primary journey: **Request a repair**; supporting navigation includes services and educational pages.

## Images and claims
Homepage hero now uses responsive `rushx-workshop-{320,640,1280}.webp` assets via the storytelling asset registry. Preserve meaningful alt text, dimensions/aspect ratios, responsive loading, and accessible contrast. The source/provenance must be verified before making any real-world workshop or technician claim. Other conceptual scenes must not be presented as actual facilities, diagnostics, certifications, or results. Consult `docs/visual-storytelling/asset-manifest.json` and `frontend/src/pages/public/storytelling/assets.json`.

## UI acceptance
Check at 320, 375, 768 and 1280 px where practical; both themes; keyboard access, focus, semantic labels, error/empty/loading states, mobile overflow and image layout shift. Avoid unrelated redesigns. Preserve login, OTP, repair forms, and protected routes. Run existing frontend build, unit and browser tests; distinguish executed tests from recommendations.
