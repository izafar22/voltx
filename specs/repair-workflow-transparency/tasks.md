# Repair workflow transparency — implementation task plan

Prepared 2026-11-24 from the owner-approved
[requirements](requirements.md) and [final design](design.md).

Status: **IMPLEMENTED AND LOCALLY VALIDATED.** The owner authorized implementation
on 2026-11-24. Merge, staging deployment and production deployment remain separate
approval gates.

The approved deliverable is the trust-led RushX Lifecycle Ring: eight selectable
repair milestones, a continuously advancing but pausable explanatory loop,
illustrative WhatsApp milestone bubbles, one selected-stage detail panel and the
existing booking/tracking actions. No additional marketing section or alternative
visual direction is included.

## Delivery decision

Implement the approved experience with semantic React, CSS and SVG as the primary
medium. The approved visual does not require WebGL, Blender, Three.js or React
Three Fiber. Do not add a graphics runtime unless a separately reviewed spike
proves that it materially improves comprehension while meeting the existing
budgets. The initial public page, complete interaction and fallback must work
without a canvas.

This feature is presentation-only. It must not change repair statuses, estimate
decisions, payment behavior, WhatsApp templates or delivery, consent, authentication,
provider configuration, customer data or backend workflow logic.

## Approval gates

| Gate | Status | Required evidence / next action |
| --- | --- | --- |
| Requirements | APPROVED | Final requirements approved 2026-11-23 |
| Visual design | FINAL APPROVED | Lifecycle Ring and canonical logo finalized 2026-11-24 |
| Task plan | APPROVED | Owner authorized implementation 2026-11-24 |
| Runtime implementation | COMPLETE | RWT-01 through RWT-10 implemented, locally validated and handed off in PR #82 |
| PR review and merge | NOT AUTHORIZED | Passing CI, review findings resolved and explicit merge approval |
| Staging deployment | NOT AUTHORIZED | Normal staging CD after authorized merge; verify exact active revisions |
| Production promotion | NOT AUTHORIZED | Separate release selection, exact-SHA approval and deployment verification |

## Dependency map

| Task | Deliverable | Depends on | Status |
| --- | --- | --- | --- |
| RWT-01 | Baseline audit and frozen content contract | Implementation approval | DONE |
| RWT-02 | Pure lifecycle data model and semantic component contract | RWT-01 | DONE |
| RWT-03 | Accessible ring, selected-stage panel and message preview | RWT-02 | DONE |
| RWT-04 | Living motion controller, pause behavior and persistence rules | RWT-03 | DONE |
| RWT-05 | Responsive visual polish, themes and canonical branding | RWT-03, RWT-04 | DONE |
| RWT-06 | Homepage and How-it-works integration | RWT-02 through RWT-05 | DONE |
| RWT-07 | Public copy, Delhi/NCR metadata and crawlable content | RWT-01, RWT-06 | DONE |
| RWT-08 | Unit, accessibility and interaction regression coverage | RWT-02 through RWT-07 | DONE |
| RWT-09 | Browser, performance and fallback acceptance | RWT-05 through RWT-08 | DONE |
| RWT-10 | Context, validation evidence and implementation PR | RWT-01 through RWT-09 | DONE |

## RWT-01 — Baseline audit and frozen content contract

Before editing, record the active branch and inspect the existing public page,
storytelling components, `RepairJourney`, routes, metadata, public browser tests,
Storybook stories and sitemap behavior. Confirm the current `/` and
`/how-it-works` compositions and identify all geography copy that conflicts with
the approved Delhi/NCR-only acquisition phase.

Create one reviewed, immutable presentation contract for the eight public stages:

1. Request received;
2. Accepted for inspection;
3. Charger received;
4. Estimate ready;
5. Approval recorded;
6. Repair result and balance;
7. Payment received; and
8. Return dispatched.

For each stage record its short label, full heading, explanation, illustrative
message, charger location, next actor and customer-control note. Use only generic
fictional content. Reconcile the contract with the approved WhatsApp lifecycle
meaning, but do not import provider template copy or create a dependency on live
template configuration.

Acceptance:

- The content contract has exactly eight ordered stages and stable identifiers.
- Each stage distinguishes recorded fact from next action and contains no personal
  data, invented time, repair guarantee or facility claim.
- Request receipt is not inspection acceptance; acceptance is not repair approval;
  completion is not payment receipt; dispatch is not delivery.
- The audit names the existing source files to be replaced or reused and records
  any mismatch in `context/` rather than treating documentation as runtime proof.

## RWT-02 — Pure lifecycle model and semantic component contract

Add a pure public lifecycle component under the existing public storytelling or
shared pattern structure. Keep stage data separate from rendering. The component
accepts the reviewed stages and optional initial stage, and exposes no API, auth,
repair mutation, payment or messaging hooks.

Render all eight stages as native buttons in DOM order with stable labels and
selected state. The active stage updates one semantic heading, description,
location, next actor, customer-control note and illustrative WhatsApp message.
Use an `aria-live="polite"` summary for deliberate stage changes without announcing
animation frames. Previous, next and direct-stage selection must share one state
transition path.

Acceptance/tests:

- Exactly one stage is selected and reported with `aria-pressed` or equivalent
  tab semantics.
- Keyboard and pointer activation produce identical content.
- Previous wraps from stage 1 to stage 8 and Next wraps from stage 8 to stage 1,
  matching the explanatory loop without changing browser history.
- Essential stage names and explanations are real HTML, not SVG text, generated
  pseudo-content or canvas-only content.
- The component renders useful content with JavaScript motion disabled.

## RWT-03 — Approved Lifecycle Ring interface

Build the approved circular ring with a lightweight SVG progress track and CSS
positioned stage controls. Reproduce only the frozen composition:

- trust-led hero: **“A repair system you can see, trust, and follow.”**;
- restrained hero type scale from the approved reference;
- prominent, readable stage names such as Request and Accepted;
- RushX core, stage progress, current/completed/upcoming states;
- one floating illustrative WhatsApp bubble synchronized to the active stage;
- one selected-stage detail panel; and
- Book a repair and Track a repair actions using existing routes.

Use the actual shared `Logo` component and
`frontend/src/assets/brand/rushx-mark.svg`. Do not redraw the mark, use a generic
Zap icon or introduce another logo file.

Acceptance/tests:

- All eight stage controls remain visible and distinguishable without relying on
  color alone.
- Active-stage movement updates the progress path, bubble and detail panel as one
  coherent state.
- Message previews are marked illustrative and never resemble a live customer
  conversation or imply guaranteed delivery.
- The estimate stage clearly explains the customer decision. Any illustrative
  decision control is inert and explicitly labelled as a demonstration.
- Existing booking, tracking, navigation, theme and support links retain their
  routes and security boundaries.

## RWT-04 — Living motion and customer control

Implement the approved living motion language with CSS/SVG animation:

- breathing RushX core and recorded-status signal;
- softly travelling progress light;
- floating/pulsing active stage;
- short message-arrival transition and subtle activity indicator; and
- smooth stage changes using transform and opacity rather than layout animation.

Automatic explanation advances at a calm, reviewed interval. Pointer hover anywhere
inside the lifecycle, keyboard focus entering it, the visible Pause control,
document visibility loss and off-screen state pause automatic advancement and
ambient motion. Resume only when the applicable pause reason is cleared; an
explicit user pause must not be undone by pointer leave. Touch users must have the
same visible Pause/Play control.

Respect `prefers-reduced-motion: reduce`: no automatic advancement, breathing,
orbiting, floating, pulsing, parallax or animated message arrival. Direct controls
must still switch stages immediately.

Acceptance/tests:

- A small state machine distinguishes explicit pause, hover/focus pause,
  off-screen pause and hidden-document pause so event order cannot restart motion
  incorrectly.
- Hovering or focusing pauses; leaving restores only a previously running loop.
- Explicit Pause remains paused after hover/focus changes and updates
  `aria-pressed` plus its visible label.
- Timers, observers and listeners clean up on unmount and do not duplicate under
  React Strict Mode.
- Reduced-motion tests prove no timer-driven stage changes occur.

## RWT-05 — Responsive polish, themes and fallback

Implement the approved spatial/glass treatment using existing semantic tokens,
Outfit display typography, Manrope body text and IBM Plex Mono identifiers. Keep
RushX green as the active-system signal and preserve familiar WhatsApp green only
inside the illustrative message cue. Do not copy Apple assets or proprietary
WhatsApp chrome.

Compose distinct layouts for desktop/tablet/mobile rather than shrinking the
desktop ring. At 320px and 375px, keep stage labels at a readable size, prevent the
message bubble from causing horizontal overflow, keep touch targets approximately
44px, and place the detail panel below the ring. At 768px and 1280px, preserve the
ring hierarchy without overlap between nodes, bubble and detail panel.

The semantic React/CSS/SVG implementation is also the fallback. It must remain
complete when motion, backdrop filters or advanced visual effects are unavailable.

Acceptance/tests:

- Light and dark themes maintain readable foreground/background pairings.
- No clipped stage label, message, CTA or horizontal page overflow at 320, 375,
  768 or 1280px.
- Focus indicators remain visible above glow and glass effects.
- `forced-colors`/high-contrast and reduced-motion states preserve labels,
  selection and controls even when decorative effects disappear.
- The canonical mark stays undistorted and the wordmark remains live text through
  `Logo.jsx`.

## RWT-06 — Homepage and How-it-works integration

Integrate the concise trust-led lifecycle experience into the existing public
site without adding the removed “Every stage explained” grid or other alternative
design sections. Reuse a single production component/data contract rather than a
parallel homepage mock and How-it-works implementation.

The homepage should communicate the journey at a glance and link to the complete
How-it-works route. The How-it-works page provides the full eight-stage interaction,
selected-stage detail and CTAs. If the complete ring fits the measured homepage
layout/performance budgets, reuse it there; otherwise render a reviewed concise
mode from the same component and data, never a second hard-coded lifecycle.

Acceptance/tests:

- `/` and `/how-it-works` each have one logical H1 and correct heading order.
- Homepage and detailed journey use the same stage source and cannot drift.
- Book a repair resolves to `/repairs/new`; Track a repair resolves to `/repairs`;
  the homepage overview links to `/how-it-works` where applicable.
- Existing header, footer, login, policy routes, floating support link and public
  navigation continue to work.
- No unrelated homepage redesign, new lead form or tracking code is introduced.

## RWT-07 — Delhi/NCR content, metadata and search visibility

Update public copy and route metadata so this customer-acquisition phase clearly
targets Delhi/NCR. Remove or qualify current public-page claims that market Mumbai,
Bengaluru, unrestricted India-wide courier repair or nationwide onsite service.
Keep the independent multi-brand/no-manufacturer-authorization statement.

Set a natural page title, meta description, canonical and social metadata for the
How-it-works route and homepage. Ensure `/how-it-works` remains present in the
existing sitemap and `llms.txt` behavior. Do not add unsupported LocalBusiness
fields, ratings, testimonials, service areas, prices or turnaround promises.

Acceptance/tests:

- Visible copy and metadata contain Delhi/NCR naturally and do not keyword-stuff.
- Search-visible HTML explains inspection acceptance, customer estimate approval,
  account fallback and optional WhatsApp milestones without requiring animation.
- Automated assertions reject the removed geography/promises on the affected
  acquisition surfaces.
- Canonical URL, title and description update correctly during SPA navigation and
  cleanup does not leave stale tags.
- Sitemap/SEO backend tests remain green; no signed-in route enters the sitemap.

## RWT-08 — Unit, Storybook and accessibility verification

Add production-component stories for representative stages: request, estimate
decision, repair result/balance and return dispatch. Include light/dark,
running/paused and reduced-motion review states using fictional content only.

Add focused React tests for stage selection, wrapping Previous/Next, content
synchronization, pause state precedence, focus/hover behavior, cleanup and
reduced-motion. Extend existing public-page tests for approved headings, copy,
links, geography and canonical logo reuse.

Acceptance:

- No story imports auth providers, APIs, repair data or live provider code.
- Automated axe checks find no A/AA violations in the tested compositions;
  manual review still covers reading order, keyboard traversal and announcements.
- Tests use fake timers deterministically and restore browser globals after each
  case.
- No test relies only on snapshots for interaction or semantic correctness.

## RWT-09 — Browser, performance and fallback acceptance

Extend `frontend/e2e/public.spec.cjs` and the Storybook browser suite. Exercise the
real homepage and How-it-works implementation at 320, 375, 768 and 1280px in both
themes. Verify keyboard-only selection, Pause/Play, hover/focus pausing,
reduced-motion, no overflow, route links and runtime-console cleanliness.

Measure rather than assume the design budgets:

- the public heading and primary CTA render without waiting for lifecycle motion;
- no added WebGL/3D runtime;
- added compressed public JavaScript remains at or below the design target of
  180 KB and any new visual asset remains within the 350 KB target;
- animation uses transform/opacity/SVG properties and remains responsive on the
  representative Android device selected during implementation;
- lifecycle animation pauses off-screen and while the document is hidden; and
- no external asset request, analytics call or customer/provider request is added.

If the budgets or mobile behavior fail, simplify blur, glow, node motion or the
homepage mode before considering a larger library. Do not waive the budgets to
preserve decoration.

## RWT-10 — Documentation, validation and implementation PR

Update `context/ui-context.md`, `context/architecture.md` and
`context/progress-tracker.md` with the actual implementation, chosen medium and
verified results. Update design-system documentation only where the shared logo or
public pattern contract genuinely changed. Create
`specs/repair-workflow-transparency/validation.md` containing the exact commands,
results, skips, warnings, reviewed screenshots and performance measurements.

Audit the final diff for secrets, personal data, unapproved geography, misleading
claims, external calls, new dependencies and unrelated repair/auth/payment/
WhatsApp behavior. Open a PR against the current approved integration branch with:

- scope and customer outcome;
- exact tests and builds run;
- mobile/desktop/light/dark/reduced-motion evidence;
- bundle/performance evidence;
- risks and compatibility;
- context documentation changes; and
- rollback instructions.

Resolve review comments and rerun checks affected by each fix. Merge only after
explicit owner approval. After an authorized merge, observe normal staging CD and
verify the active frontend and backend revisions with the restricted staging check.
Production promotion remains a separate exact-SHA approval under
`docs/DEPLOYMENT_REQUIREMENTS.md`.

## Suggested verification commands

Record actual results in `validation.md`; do not mark them passed in advance.

```sh
cd frontend
yarn test --watchAll=false --runInBand
yarn build
yarn build-storybook
cd e2e
npm ci
npx playwright install chromium
npm test
npx playwright test --config storybook.playwright.config.cjs

cd ../..
pytest -q backend/tests/test_studio_cms.py backend/tests/test_seo_files.py
```

Run repository-wide required CI commands in addition to these focused checks when
implementation begins. Browser screenshot updates require deliberate review; do
not automatically accept changed baselines.

## Rollback and compatibility

The implementation is a public presentation change and requires no schema or data
migration. Rollback is the previous frontend artifact/commit. The existing public
routes, repair booking, tracking, account, backend APIs and WhatsApp lifecycle
remain compatible because the feature does not alter them. If a release is rolled
back, restore the complete approved frontend artifact rather than selectively
removing CSS while leaving component markup or stage content behind.

## Explicitly deferred

- Any backend repair-state, estimate, payment or WhatsApp change.
- Real customer messages, live template edits or provider sends.
- WebGL, Blender, Three.js or React Three Fiber unless separately justified and
  approved after the CSS/SVG implementation is measured.
- New location pages, structured business claims, testimonials, case studies,
  analytics, advertising or conversion tracking.
- New pickup, courier, pricing, warranty, repair-success or turnaround promises.
- A second lifecycle grid, alternate design direction or additional promotional
  sections removed during final design review.
