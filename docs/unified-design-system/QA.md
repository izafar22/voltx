# Issue #17 — unified RushX experience

## Branch, dependencies and review plan

`feature/rushx-unified-design-system` starts from unmerged PR #14 (`feature/rushx-public-service-education`, commit `1eb3a6f`). The draft PR targets that feature branch, not production. It reuses the foundation patches from PR #16 (`3417171`, `355beaa`) by cherry-pick; neither existing PR branch is overwritten or merged. The new work extends those foundations to login/dashboard copy, reusable layouts/CTAs/empty states/sidebar, pre-paint initialization and full before/after evidence.

PR #16 overlaps this consolidation. Review one coherent design-system change rather than merging both duplicated patch sets independently. Once PR #14 is separately authorized and integrated, retarget/rebase the selected design-system PR onto `repair-mvp` and rerun tests. PR #12 is excluded; its eventual integration needs its own OTP regression pass. Existing Git stashes remain untouched.

## Audit and incremental migration

| Surface | PR #14 baseline | Unified result |
| --- | --- | --- |
| Public education | Cream/olive hardcoded interface, no public theme switch | Existing layout/content/illustration with semantic app surfaces, readable green roles and shared toggle |
| Login | Inverse desktop panel, no explicit toggle/public return; “of any brand” claim | Same two-column/mobile form layout, shared neutral surfaces, repair-first mission, feasibility caveats, public links and shared toggle |
| Customer dashboard | Existing neutral theme; “any brand” promotion, one-off empty state; no direct public return | Existing dashboard structure, qualified shared RepairCTA, shared Card/EmptyState and SidebarLinks with Explore RushX |
| Foundations | Shared Logo/fonts/green but divergent surfaces and control sizing | One CSS token contract, same ThemeProvider, existing Logo/Lucide/fonts, consistent focus/input/card/action roles |
| First paint | Theme applied only after React initialization | Read-only blocking bootstrap matches the same validated persisted/system preference before app bundles load |

[DESIGN_SYSTEM.md](../DESIGN_SYSTEM.md) records palette provenance, tonal proposals, semantics, spacing/radii, state rules, accessible pairings and Storybook usage. No unrelated identity, B2B workflow, endpoint, cookie, credential, repair transition or WhatsApp consent change was introduced.

## Verification

- **158 frontend tests** passed across 14 suites, including existing SMS OTP, registration, Google return destination, feature gates, repair requests, payments and WhatsApp consent regressions.
- **52 public/application browser checks** passed at **320, 375, 768 and 1280px**. Each real homepage/login/dashboard is audited in both themes for overflow and axe WCAG 2 A/AA and 2.1 AA rules. Theme continuity, refresh, public return, keyboard navigation, the existing SMS-to-repair flow, same-origin Google entry and simulated callback-to-repair destination are covered.
- **119 Storybook checks** passed: **28 stories**, two themes, mobile/desktop, accessibility, strict existing macOS visual baselines, theme persistence/network isolation and real manager theme/viewport controls. Reviewed Linux baselines from PR #16 are retained without automatic updates. The addon remains manual-on-demand; Playwright owns automated scans to avoid concurrent axe engines.
- App production build and static Storybook build both passed. Storybook uses the existing React/Webpack/Tailwind stack, not a second application framework. Run `cd frontend && yarn storybook`; see the frontend README for all commands.
- New regressions cover pre-paint preference precedence, invalid/blocked storage, public navigation from authenticated surfaces, and qualified login copy. Auth handlers/payloads remain in Login; pure Storybook presentation components do not import auth/API providers.
- Representative mobile/desktop screenshots were visually reviewed for hierarchy, brand, contrast, form/CTA placement, clipping and qualified messaging. Existing CSS reduced-motion rules and keyboard focus remain active.

## Before/after screenshots

Before images come from a production build of PR #14 at `1eb3a6f`, before applying PR #16's patches. After images come from this branch's production build. Every screenshot uses synthetic/empty customer data, mocked local APIs and blocked external requests. The existing fonts fall back deterministically when remote font delivery is blocked. No real Google exchange, SMS, WhatsApp delivery or customer data was used.

Desktop (1280px):

| Page | Before light | After light | Before dark | After dark |
| --- | --- | --- | --- | --- |
| Homepage | [before](screenshots/before/1280/home-light.png) | [after](screenshots/after/1280/home-light.png) | [before](screenshots/before/1280/home-dark.png) | [after](screenshots/after/1280/home-dark.png) |
| Login | [before](screenshots/before/1280/login-light.png) | [after](screenshots/after/1280/login-light.png) | [before](screenshots/before/1280/login-dark.png) | [after](screenshots/after/1280/login-dark.png) |
| Dashboard | [before](screenshots/before/1280/dashboard-light.png) | [after](screenshots/after/1280/dashboard-light.png) | [before](screenshots/before/1280/dashboard-dark.png) | [after](screenshots/after/1280/dashboard-dark.png) |

Mobile (375px):

| Page | Before light | After light | Before dark | After dark |
| --- | --- | --- | --- | --- |
| Homepage | [before](screenshots/before/375/home-light.png) | [after](screenshots/after/375/home-light.png) | [before](screenshots/before/375/home-dark.png) | [after](screenshots/after/375/home-dark.png) |
| Login | [before](screenshots/before/375/login-light.png) | [after](screenshots/after/375/login-light.png) | [before](screenshots/before/375/login-dark.png) | [after](screenshots/after/375/login-dark.png) |
| Dashboard | [before](screenshots/before/375/dashboard-light.png) | [after](screenshots/after/375/dashboard-light.png) | [before](screenshots/before/375/dashboard-dark.png) | [after](screenshots/after/375/dashboard-dark.png) |

The browser suite also generates after screenshots for all four widths in ignored `frontend/e2e/test-results/unified`, uploaded by CI. Committed snapshots are review evidence, not automatically approved visual changes.

## Review / staging checklist

- [x] Existing logo, font families and brand-green accents reused; semantic light/dark roles shared.
- [x] Public, login and dashboard layouts retained and responsive at all four target widths.
- [x] Repair-first copy replaces unsupported blanket repair claims in login/dashboard.
- [x] Shared toggle persists across route changes and refresh; initial system preference and blocked storage are tested.
- [x] Public educational links work from login, customer navigation and owner/admin shell navigation.
- [x] Existing phone/Google/repair destinations retained; no new auth or backend implementation.
- [x] Component, browser, axe, Storybook and production build checks passed locally; before/after evidence captured.
- [ ] In a separately approved staging environment, repeat real provider sign-in, registration, repair submission/tracking and sandbox WhatsApp-consent checks using test accounts only.
- [ ] Human review with assistive technology and actual supplied fonts, plus palette proposal approval.
- [ ] Resolve PR #14 / #16 integration order before any future merge, then rerun full CI. No merge or release is part of this task.

## Outstanding issues and limits

1. PR #14 is an explicit unmerged dependency; PR #16 contains overlapping foundational work. Neither has been merged by this task. The draft identifies the consolidation and integration path.
2. Automated tests use safe mocks. They verify routes and UI behavior, not live Google/SMS delivery, production cookies/proxy rewrites, WhatsApp delivery or production configuration readiness.
3. Automated axe checks are not a complete accessibility certification. Screen-reader/manual testing, external font delivery and legacy charging/map/admin workflows remain separate review areas. No B2B or multiple-unit experience was added.
4. The public site remains client-rendered: JavaScript-disabled crawlers/social preview agents may not see unique route metadata. This existing hosting/SEO limitation is unchanged.
5. The pre-existing frontend npm app lock remains legacy; Yarn is authoritative as declared by package.json and CI. The isolated e2e package continues to use its npm lock.
6. Per the requested stopping point, this task stops after opening the draft PR. CI runs automatically on push; no merge, deploy, production configuration or MongoDB modification is performed.
