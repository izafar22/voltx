# RushX design system

The living reference is React Storybook (`cd frontend && yarn storybook`). The implementation contract is `frontend/src/design-system/tokens.css`, existing shared UI primitives, and the pure repair patterns. Stories import those components directly. This document explains the decisions; it is not an independent stylesheet or permission to rebrand RushX.

## Audit and provenance

Issue #15 builds on PR #14 at `1eb3a6f`, which remains unmerged. The new branch is stacked on `feature/rushx-public-service-education`; its draft PR targets that branch so reviewers see only design-system work. Merge/review #14 separately first, then retarget this PR to `repair-mvp` and rerun checks. Do not overwrite #14 or cherry-pick its pages into production as part of this task. OTP PR #12 is not included. Its shared App/Login/CI work needs integration testing when it is eventually reviewed; this branch does not change auth endpoints, OTP logic, cookies, Google OIDC, WhatsApp consent or backend state machines. Existing Git stashes are retained.

### Existing source facts

- Product name: RushX; website identity: EVChargerRepair.in; mission: “Repair when possible. Replace when necessary.”
- Existing `Logo.jsx`: a black Lucide Zap on a green rounded square, with RushX wordmark. No replacement mark, photograph or logo asset is introduced.
- Existing app green: light `147 100% 39%` (approximately `#00c759`); dark `151 100% 45%`. These exact `--charging` / `--accent` hues are retained. They are accents, not body-text colors on white.
- Existing app neutral surfaces and inverse primary buttons: white/near-black in light mode, near-black/white in dark mode. These remain the canonical common UI palette.
- Existing fonts: Outfit headings, Manrope body, IBM Plex Mono identifiers/numbers. Existing Google Fonts imports remain; system fallbacks work when fonts are unavailable.
- PR #14 introduced a parallel cream/olive public palette (`#fafbf7`, `#172e25`, pale olive surfaces) and CSS-only illustration. Its content, route semantics, layout and illustration are retained, but interface colors now consume the common app roles. Illustration-specific colors remain illustrative artwork, not a second token palette.
- The application is React 18, CRACO/react-scripts with Webpack 5, Tailwind 3, Radix primitives, class-variance-authority and Lucide. CI uses Yarn 1.22.22. Storybook 10.6.5 uses that same React/Webpack architecture, with the SWC compiler addon. No Vite application, second React runtime or paid visual-review service is added.

### Proposed decisions in this draft (review required, not asserted as formal brand approval)

1. Prefer the existing app's neutral surfaces and existing green over treating PR #14's cream/olive interface as a new brand standard. Public headings/body/buttons now use the same roles as authenticated screens. The public layout and education copy are preserved.
2. Add a readable tonal green for text/focus and subtle green surfaces derived from the existing hue. This does not replace the logo green.
3. Increase light muted-text contrast, input boundaries and focus visibility. Correct destructive text/button pairings in both themes. These are accessibility-oriented tonal deviations from the previous CSS values, explicitly listed below.
4. Use 44px minimum interactive controls (48px large buttons), a 4px spacing base, 0.6rem control radius and 1rem card radius. Most were already present in app CSS; dense 32/36px default controls are raised. Explicit page sizing still takes precedence through existing class merging.
5. Keep status labels neutral and text-based. Do not introduce a new color-coded repair lifecycle or alter the backend's states.

These proposals are implemented for review in the draft branch only. No approval, release or production infrastructure change is implied.

## Semantic token contract

Values are HSL triples so Tailwind opacity modifiers remain compatible. Use `hsl(var(--role))` in CSS or existing Tailwind classes (`bg-background`, `text-foreground`, `border-border`). The token file is imported once by the app's global CSS and therefore by Storybook.

| Role | Light | Dark | Usage / provenance |
| --- | --- | --- | --- |
| background / foreground | `0 0% 100%` / `240 6% 4%` | `0 0% 2%` / `0 0% 98%` | Existing app canvas and readable text |
| card / card-foreground | white / near-black | `0 0% 7%` / near-white | Existing elevated content |
| primary / primary-foreground | `240 6% 6%` / white | near-white / `0 0% 4%` | Existing inverse primary action; use paired foreground |
| secondary, muted | `240 5% 96%` | `0 0% 12%` | Existing quiet surfaces, not disabled text |
| muted-foreground | `240 4% 40%` | `0 0% 63%` | Light was 46%; darker proposed to remain readable on muted surfaces |
| charging, accent | `147 100% 39%` | `151 100% 45%` | Exact existing brand accent |
| accent-foreground, on-brand | near-black | near-black | Light accent foreground was white; dark label proposed for contrast |
| brand-foreground, ring | `147 70% 27%` | `151 100% 65%` | Proposed derived green for readable labels and visible focus |
| brand-surface / brand-border | `147 45% 95%` / `147 25% 70%` | `147 25% 10%` / `147 25% 35%` | Proposed quiet brand surfaces; pair with foreground text |
| border | `240 6% 90%` | `0 0% 16%` | Existing decorative separators/card edges |
| input | `240 4% 55%` | `0 0% 45%` | Proposed stronger control boundary; formerly matched decorative border |
| destructive / destructive-foreground | `3 80% 42%` / white | `5 90% 66%` / near-black | Proposed red tonal pairing; dark error text and filled action both remain readable |
| wallet, chart-1…5 | unchanged | unchanged | Existing feature/chart colors; no new blanket accessibility claim for chart combinations |

Do not use bright `text-charging` for small text on a white surface. Use `brand-foreground` instead. Error text must accompany an invalid state; color never substitutes for explanation. Test any new combination, opacity or overlay, including hover, rather than assuming every token pair is accessible.

## Typography, geometry and responsive rules

- Body: `--font-body` (Manrope), default 16px. Headings: `--font-display` (Outfit), weight 500–600. Identifiers: `--font-code` (IBM Plex Mono). Existing public fluid heading sizes remain; no unrelated typographic rebrand.
- One h1 per page and a logical heading sequence. A CardTitle's generic wrapper does not create a semantic heading: supply an h2/h3 when needed. Keep line lengths around 65 characters for explanatory copy. Do not truncate essential service limitations.
- Spacing: `--space-1/2/3/4/5/6/8/12/16` = 4/8/12/16/20/24/32/48/64px at the default root size. Use Tailwind equivalents or the tokens. Layout-specific existing measurements are not mechanically rewritten.
- Radii: `--radius` 0.6rem for controls, `--radius-card` 1rem for content cards. Existing `rounded-md/lg` derive from the control token; no promise that every legacy radius has been migrated.
- Borders: 1px semantic separators; input boundaries use `input`, not subtle `border`. Focus uses a visible 2px ring or 3px outline with offset. Shadows: `--shadow-card` restrained; `--shadow-overlay` for menus. Borders and text must communicate hierarchy without shadows alone.
- Existing Tailwind breakpoints remain 640/768/1024/1280/1536px. Education cards/layout retain PR #14's responsive rules; the public header collapses at 900px because the added shared theme control would otherwise squeeze tablet links. This is a documented content-fit exception, not a second global breakpoint scale.
- Review at 320 and 375px as well as 768 and 1280px. No horizontal scroll, clipped labels or layout dependence on hover. Respect `prefers-reduced-motion` (global motion reduction plus pattern override).

## Shared themes and components

`ThemeProvider` owns the document `.dark` class, native `color-scheme`, and validated `rushx-theme` localStorage preference. It falls back to the system preference at initialization, accepts only light/dark, works when storage is blocked, and synchronizes storage events across tabs. No live system-preference listener is added after initialization; explicit user preference wins. Tests exercise persistence, invalid storage, blocked storage, controlled use and cross-tab changes.

Storybook's toolbar controls this same provider through its optional `theme` / `onThemeChange` props. The shared ThemeToggle updates the toolbar and persistence; there is no independent Storybook theme stylesheet. Background controls are disabled intentionally so the canvas always reflects the semantic app background. Viewport controls cover 320/375 mobile, 768 tablet and 1280 desktop. The preview iframe changes theme; the Storybook manager chrome follows Storybook's own defaults.

The manageable migration includes Button/Input touch sizes and focus, shared ThemeToggle in public/customer/owner/admin shells, token-based public interface colors, dashboard card geometry, extracted ServiceCard/RepairJourney/FAQ, and RepairStatus used in list/detail screens. Authentication forms and repair business behavior remain untouched. Other legacy one-off colors, estimate-status combinations, map/chart UI, unused Navbar/Footer and remaining layout dimensions are explicitly outside this first migration; do not interpret this as a full visual certification of every screen.

- Button: primary for the next action, outline/secondary for alternatives, destructive only for destructive actions. Navigation uses `asChild` with a Link. Keep a visible label when loading, disable duplicate actions, and use `aria-busy`; do not replace meaning with a spinner alone. Loading is shown as a composition of existing props, not new business logic.
- Input: always provide a visible label, stable id and help/error association. Use `aria-invalid` and `aria-describedby` for errors. Do not use placeholders as labels. Disabled is not read-only; choose deliberately.
- Card/Badge: reuse existing primitives and role pairs. A badge should state the status; it is not a button. RepairStatus uses the existing enum-to-label map and never changes workflow transitions.
- Pure repair patterns accept content props and import their own stylesheet. They have no auth hooks or network effects. ServiceCard uses a real router Link; FAQ uses native details/summary keyboard semantics. Stories use MemoryRouter; production uses the existing BrowserRouter.
- Logo/Lucide: reuse the existing mark and icon family; decorative icons get `aria-hidden`. Every icon-only action needs an accessible name.

## Isolation and automated review

Stories mount ThemeProvider and MemoryRouter, never AuthProvider or application API/query hooks. Only approved public copy and obvious illustrative identifiers are used. No `.env` loader, credentials, private assets, real customer data, live SMS, Google exchange or production write is used. Preview blocks external/API fetch and XHR; CSP limits connections to the same origin and blocks form submission. There is no app/API proxy in either Storybook dev or the test static server. Do not add one. Browser checks also abort external resource requests.

CI builds the app and static Storybook, runs every story from the generated index at 375/1280px in light/dark, applies axe WCAG 2 A/AA and 2.1 AA checks, checks overflow/runtime errors and verifies the shared theme/network guard. Existing public browser checks cover 320/375/768/1280 and theme continuity through login and a mocked authenticated screen. Axe catches only automated rules; keyboard, reading order, copy clarity and real assistive-technology behavior still need human review.

The pinned Playwright Chromium version is shared with the existing isolated e2e package. Visual baselines cover ServiceCard compositions in both themes at mobile/desktop. OS-specific baselines avoid silently tolerating macOS/Linux font rasterization differences. Tests block remote fonts and use deterministic system fallback; these baselines do not validate Google's font delivery. macOS baselines are generated/reviewed locally; Linux baselines are bootstrapped in the isolated CI runner, then committed and tested in strict comparison mode. Normal CI must not update baselines automatically.

```sh
cd frontend
yarn install --frozen-lockfile
yarn storybook
yarn build-storybook
yarn test --watchAll=false --runInBand
yarn build
cd e2e
npm ci
npx playwright install chromium
npm test
npx playwright test --config storybook.playwright.config.cjs
# Deliberate visual update on the target OS, after reviewing the code change:
npx playwright test --config storybook.playwright.config.cjs --update-snapshots
```

Review image diffs and full-size light/dark screenshots before committing new baselines. The comparison tolerance is 0.2% pixels, with animations disabled; it is not a blanket visual approval. CI uploads failures and screenshots under `storybook-review-results`; download Linux snapshots from that artifact only after checking the corresponding commit and images. Never set `--update-snapshots` in normal CI. Yarn is authoritative for the app (`package.json` declares Yarn and CI uses its frozen lock); the pre-existing npm app lock is legacy and is not used for this change. `frontend/e2e` retains its separate npm lock for Playwright/axe tooling.

## Review checklist and future changes

1. Inspect the existing token roles and component story before adding code. Reuse actual shared components; avoid copies maintained only in Storybook.
2. Review both themes, all relevant states (hover, keyboard focus, disabled, loading, error) and mobile/desktop. Keep correct semantics and readable paired foregrounds.
3. Add a story with useful controls, test data only, and documentation. The generated manifest automatically adds it to accessibility smoke checks.
4. Run app tests/build, Storybook build/checks and public browser regressions. Review screenshots; explain every intentional baseline change.
5. Describe palette deviations as review proposals with source/contrast rationale, not invented “approved” brand guidelines. No rebranding, production configuration, release or merging follows automatically from a design-system change.

No deployment is configured for Storybook. `storybook-static` is ignored build output; CI artifacts and the draft PR are the review surfaces. The branch requires PR #14 integration first. Later OTP PR #12 integration must retain its behavior and rerun both feature suites; do not merge it just to make these stories work.

## Evidence for this draft

Local validation: **151 frontend tests**, **99 Storybook browser checks** (23 stories in two themes/two widths plus visual/theme/manager checks) and **36 public/app browser checks** passed. Both production app build and static Storybook build pass; `yarn storybook --ci` served the manager successfully on loopback. The public homepage is additionally checked with axe in light and dark modes. Representative reviewed screenshots:

- [Storybook desktop / dark](design-system/screenshots/storybook-desktop-dark.png)
- [Public homepage / dark](design-system/screenshots/public-desktop-dark.png)
- [Illustrative customer screen / dark](design-system/screenshots/customer-desktop-dark.png)
- [Mobile service cards / light](../frontend/e2e/storybook-snapshots/darwin/375/services-light.png)
- [Mobile service cards / dark](../frontend/e2e/storybook-snapshots/darwin/375/services-dark.png)

The first CI run is an explicit Linux baseline bootstrap. Final evidence must be a subsequent normal run with committed Linux images and no automatic baseline updates. All displayed customer data is synthetic.
