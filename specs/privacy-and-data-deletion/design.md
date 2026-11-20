# Privacy and data-deletion pages — design proposal

Status: APPROVED 2026-11-20. Implementation follows this design; Meta app publication and production deployment remain separate actions.

## Experience

Both pages use the active RushX public shell at `/privacy-policy` and `/data-deletion`. They keep the canonical `Logo`, theme toggle, skip link, keyboard-aware mobile navigation, footer and responsive design tokens already used by the marketing pages. They require no sign-in.

The page body is intentionally document-like: a narrow readable column, a short eyebrow, one `h1`, an introductory paragraph, and ordered sections with semantic `h2` headings. The privacy contact is a visible `mailto:rushx779@gmail.com` link. The data-deletion page gives a direct request sequence and repeats the distinction between stopping WhatsApp updates and deleting service records.

The existing public footer gains a compact `Privacy Policy` and `Data-deletion Instructions` group. Those links appear on every active public page. The older parked footer component is not used.

## Frontend structure

- Add the two paths to the public route group in `frontend/src/App.js`.
- Add metadata entries in `PublicPage.jsx`, producing distinct titles, descriptions and canonical URLs.
- Add a small `PolicyPages.jsx` module alongside `PublicPage.jsx`. It owns the approved page copy as React markup and selects content by pathname. Keeping policy copy separate prevents the already large public-shell component from becoming a second content store.
- Render the selected policy page inside `PublicPage` and add the footer links with React Router `Link` elements.
- Add scoped `.rx-policy-*` rules to `PublicPage.css`: readable line length, heading rhythm, list spacing, link states and mobile padding. Reuse existing colors, fonts and focus behavior; introduce no independent visual system.
- Keep the pages indexable. Canonical URLs are `https://evchargerrepair.in/privacy-policy` and `https://evchargerrepair.in/data-deletion`.

## Runtime tracking removal

Remove the legacy Emergent runtime loader and inline PostHog bootstrap from `frontend/public/index.html`. Retain the theme bootstrap, Google Fonts and the unrelated build-time visual-editing package. Verify both source and generated build contain no Emergent/PostHog runtime URL, project key, global or session-recording configuration.

## Backend routing and discovery

Add both routes to `SPA_EXACT` so direct requests and refreshes return the React application instead of a Studio lookup or 404. Add both routes to `SITEMAP_STATIC` so they appear in the generated public sitemap. No API, database, migration or deletion-worker change is required.

## Validation design

- Component/router tests cover unauthenticated rendering, one page heading, approved contact link and footer navigation.
- Public Playwright coverage checks both pages at mobile and desktop sizes, in light and dark themes, including metadata, keyboard navigation, overflow and direct refresh.
- Backend route-contract and sitemap tests prove both paths are recognized and public while signed-in application routes remain absent from the sitemap.
- A production build and static scan prove the removed runtime tracking code is absent from the shipped artifact.
- Staging acceptance checks both public URLs and approved copy before either URL is entered into Meta.

## Security and operational boundaries

The pages expose only the approved business email. They contain no test phone number, customer information, secret, internal provider identifier or administrative workflow. The pages provide instructions; they do not delete data. Meta app publication, webhook routing, WhatsApp delivery testing and production deployment remain separate actions with their existing approval gates.

## Decision record

- Canonical public shell and logo reused; no separate policy microsite.
- Static, version-controlled copy chosen because these pages are operational prerequisites and must change through review.
- No consent banner added because the removed analytics/session-recording runtime is not being retained. Authentication/session and theme behavior remain disclosed.
- No fixed deletion deadline or universal-erasure promise added because the current process is manually reviewed and record-specific.
