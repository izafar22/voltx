# Repair workflow transparency — visual design

Status: DESIGN APPROVED. Based on the approved requirements at commit `183f6f4`.
Revised and approved on 2026-11-23 after owner feedback requesting greater
interactivity, simpler workflow comprehension and exact Storybook consistency.
The Lifecycle Ring direction is frozen for task planning. This approval does not
authorize implementation, dependency changes, merge or deployment.

## Design objective

Make RushX's repair workflow feel like a connected, dependable customer system:
the charger advances through verified stages, the customer keeps control of the
priced repair decision, and the dashboard plus optional WhatsApp milestones make
progress visible.

The design must communicate four facts within the first screen:

1. RushX follows a structured repair process.
2. The customer knows where the charger is in that process.
3. Repair begins only after the customer approves the estimate.
4. Optional WhatsApp milestones complement the authoritative RushX dashboard.

## Recommended concept: RushX Lifecycle Ring

The revised recommendation is a circular eight-stage lifecycle ring. It makes the
complete process visible at once while focusing one milestone at a time. The ring
advances continuously as an explanatory loop, displays the applicable illustrative
WhatsApp update beside the active stage and pauses whenever a pointer hovers over
the experience or keyboard focus enters it. A visible Pause/Play control provides
the equivalent behavior for touch users and anyone who does not hover.

Every stage is a real semantic button. A customer may select any stage directly or
use previous/next controls. Manual selection updates the ring progress, stage
description, charger location, next responsible actor and WhatsApp preview. Reduced
motion disables automatic advancement.

The circular motion is an explanatory presentation of the service lifecycle; it
must not imply that every real repair advances automatically or continuously.

### Frozen design decisions

- Use the circular eight-stage RushX Lifecycle Ring as the primary visual.
- Advance through the stages as a continuous explanatory loop.
- Show the relevant illustrative WhatsApp pop-up at the active stage.
- Pause on pointer hover and keyboard focus; provide visible Pause/Play and direct
  stage controls for touch and keyboard users.
- Keep every stage directly selectable and retain previous/next navigation.
- Follow the canonical RushX Storybook logo, Outfit/Manrope/IBM Plex Mono type,
  semantic tokens, controls and light/dark themes.
- Do not add the separate “Every stage explained in plain language” grid shown in
  an earlier prototype. It repeats the ring and makes the page unnecessarily long.
- Preserve SEO/accessibility through semantic stage buttons, the selected-stage
  heading and description, server-visible page copy and appropriate metadata,
  rather than a duplicate visible eight-card section.

### Approved visual refinement direction

The frozen structure may use a premium spatial interface treatment inspired by
the clarity and motion discipline associated with modern iOS interfaces, without
copying Apple assets, controls or typography. Retain the RushX Storybook identity
while applying:

- translucent, softly blurred layers with readable contrast in both themes;
- restrained depth, environmental glow and soft shadows instead of heavy borders;
- spring-like but non-bouncy stage selection and ring-progress transitions;
- rounded anchored WhatsApp bubbles that move smoothly to the active stage;
- pill-shaped Pause/Play and navigation controls with clear focus states;
- generous spacing and a stronger hierarchy around the selected milestone; and
- a complete reduced-motion treatment that removes automatic and spring motion.

Visual glass effects are enhancement only. Content, controls and contrast must
remain usable when backdrop filtering is unsupported.

## Supporting concept: RushX System Journey

The homepage contains a compact, three-dimensional system map. A stylized charger
travels along a luminous RushX path through four grouped stations:

1. **Request & acceptance** — enquiry received, then explicitly accepted for
   inspection with hand-off instructions.
2. **Inspect & estimate** — receipt, diagnosis and the published estimate.
3. **Approve, repair & test** — the customer decision visibly unlocks only the
   approved repair path.
4. **Payment & return** — verified balance/payment followed by actual return
   dispatch.

Selecting a station focuses it and updates a companion customer-view panel. The
panel pairs a compact RushX dashboard state with an illustrative WhatsApp bubble.
The overview never auto-advances. A clear link opens the complete journey.

The full How it works page expands the map into all eight customer milestones:

| Stage | Visual event | Customer-facing message or action |
|---|---|---|
| Request received | Charger enters the RushX path | Enquiry receipt; review comes next |
| Accepted for inspection | Intake gate opens | Approved hand-off/shipping instructions |
| Charger received | Package reaches RushX | Physical receipt confirmation |
| Estimate ready | Estimate console activates | Review and Approve/Decline demonstration |
| Approval recorded | Customer-control gate unlocks | Approval acknowledgement |
| Repair result | Charger components illuminate and reassemble | Result plus verified balance position |
| Payment received | Verified receipt indicator appears | Separate payment acknowledgement |
| Return dispatched | Charger exits toward the customer | Courier and tracking facts |

Exception paths such as declined estimate, not repairable and cancelled remain a
short, honest branch below the main journey rather than being hidden or presented
as automatic WhatsApp milestones.

## Visual language

- Preserve the existing RushX logo exactly.
- Follow the canonical Storybook foundations rather than introducing a campaign
  sub-brand: Outfit for headings, Manrope for body copy, IBM Plex Mono for stage
  identifiers, Lucide-style 1.5-stroke icons, the 32px rounded-square Zap mark,
  semantic neutral surfaces and the existing charging/brand colour roles.
- Use the existing `--radius`, `--radius-card`, `--shadow-card`, 44px minimum
  control height and shared light/dark semantic roles. The implementation must
  consume the actual tokens and components rather than copying visual values.
- Use RushX green as the single active-system signal. Retain exact WhatsApp green
  only inside the illustrative WhatsApp channel preview.
- Use a simplified, brand-led charger model rather than a specific manufacturer
  product. It must look recognizable without making a compatibility claim.
- Build spatial depth with perspective, layered planes, soft environmental light
  and restrained material response. Avoid a literal factory or real workshop.
- Represent verified events with a check pulse and explicit text, not colour alone.
- Represent customer decisions with a visible gate; repair-system movement does not
  continue until the illustrative approval state is selected.
- Keep WhatsApp previews visually familiar but not a pixel-for-pixel reproduction.
  Use fictional content, generic names and illustrative timestamps.

## Interaction model

### Homepage

- Four semantic stage buttons sit outside the visual renderer.
- Selecting a stage changes the focused station, charger position, status summary
  and message preview.
- Previous/next controls are optional on mobile; direct stage buttons remain.
- “See the complete journey” links to `/how-it-works`.
- “Book a repair” links to `/repairs/new`; “Track a repair” links to `/repairs`.

For the approved circular direction, the homepage may use the complete ring if it
fits the measured performance and layout budgets; otherwise it uses a simplified
four-phase ring linking to the full eight-stage How it works page.

The revised recommended prototype also offers an eight-stage direct-selection
rail. This lets a visitor understand the complete workflow at a glance, select any
milestone, move with Previous/Next controls, switch between RushX dashboard and
WhatsApp views, and see charger location plus the next responsible actor update in
one place. This is preferred over hiding the milestones behind a decorative scene.

### How it works

- Eight semantic stage buttons provide direct access.
- Selection updates one focused 3D scene and one concise detail panel rather than
  rendering eight heavy scenes.
- The estimate demonstration offers illustrative Approve and Decline controls.
  Both are visibly labelled as a preview and cannot call an API or change a repair.
- A declined demonstration reveals the truthful exception branch; it does not move
  the visual into repair.
- The selected stage is addressable in the page URL fragment only if this can be
  added without conflicting with existing routing and scroll behaviour.

## Motion

- Stage changes use a short camera ease, charger translation and one confirmation
  pulse. No looping animation is required to understand the scene.
- Message arrival follows the stage focus and does not imitate a live incoming
  customer message.
- With reduced motion, state changes cut directly with no camera travel, parallax,
  pulsing or moving charger.
- Rendering pauses off-screen and when the document is hidden.

## Responsive composition

- **Desktop:** scene occupies the visual centre; the customer-view panel sits
  beside it and stage controls form a clear rail below.
- **Tablet:** scene remains above a compact customer-view panel; controls wrap in
  two rows without horizontal scrolling.
- **Mobile:** use a purpose-built vertical composition. The focused charger/station
  remains visible, then the current status/message panel, then large stage controls
  and conversion actions. Do not shrink a desktop canvas to unreadable size.

## Accessibility and fallback

- The renderer is decorative to assistive technology. Stage buttons, selected
  state, concise stage details and links live in semantic HTML.
- Selected stage uses `aria-pressed` or tab semantics and an `aria-live="polite"`
  summary. Do not announce animation frames.
- The full journey exists as an ordered semantic structure in the document.
- Keyboard, touch and pointer interaction select the same states.
- A static SVG/CSS illustration presents the same selected-stage state if WebGL is
  unsupported, loading fails, data saving is active or the device is below the
  implementation-approved capability threshold.

## Search visibility design

The animated ring is progressive enhancement, not canvas-only content. All eight
stage names are real semantic controls in the DOM and the selected stage uses a
real heading and paragraph. Supporting introductory copy explains the service in
visible HTML without repeating the ring as a second eight-stage grid. The page also
needs a unique Delhi/NCR-focused title and description, one descriptive H1,
crawlable anchor links for booking/tracking, and inclusion in the public sitemap.

Do not place essential lifecycle copy only in canvas, SVG text, CSS-generated
content or a hidden interaction state. Google advises expressing visual content in
text form and using semantic HTML because canvas-rendered content is not indexed as
page text. Structured data may be evaluated separately, but must describe verified
business facts and is not a substitute for visible useful content.

## Proposed implementation medium

Recommend React Three Fiber over direct Three.js only if the implementation spike
confirms acceptable bundle and runtime cost. A small Blender-authored glTF charger
and reusable procedural stations are preferable to several baked scenes.

The implementation spike must compare:

1. React Three Fiber plus compressed glTF;
2. direct Three.js with the same asset; and
3. the SVG/CSS fallback as a possible primary experience.

Choose the lightest option that preserves the approved experience. No library is
approved by this design alone.

## Performance budgets for implementation review

- Public heading and primary CTA render without waiting for the visualization.
- Visualization code and assets load only when the journey approaches the viewport.
- Proposed compressed 3D model and textures: target at or below 350 KB transferred.
- Proposed visualization JavaScript added to the existing public route: target at
  or below 180 KB compressed, with the final figure measured in the spike.
- One renderer and one focused scene; do not render a canvas per milestone.
- Cap pixel ratio on high-density mobile devices and use adaptive quality.
- Maintain responsive interaction on the representative Android test device chosen
  during implementation planning; record measured results rather than asserting a
  performance score in advance.

Budgets are design targets, not permission to regress the rest of the public page.
If the spike cannot meet them, use the SVG/CSS concept as the primary experience.

## Content examples

Message previews use compact, truthful examples such as:

- “We received your repair request. Our team will review it before confirming the
  next step.”
- “Your charger has been accepted for inspection. Follow the approved hand-off
  instructions shown in your RushX account.”
- “Your estimate is ready. Review it and choose Approve or Decline.”
- “Repair is complete. Your verified balance is shown in your RushX account.”
- “Your charger has been dispatched. Courier and tracking details are now
  available.”

These are design examples, not approved Meta template replacements. Implementation
must use public explanatory copy and must not change production template content.

## Design acceptance checklist

- Homepage overview is understandable within one glance and one interaction.
- Complete journey preserves all eight approved milestones and decision boundaries.
- Visual design feels premium, connected and distinctly RushX without depicting a
  fictional real facility.
- Dashboard and WhatsApp have clear, complementary roles.
- Estimate approval is visually prominent and clearly demonstrative.
- Delhi/NCR positioning and truthful limitations remain visible.
- Desktop, tablet, mobile, light, dark, reduced-motion and fallback states are
  represented before task planning.
- Owner approves one visual direction before implementation tasks are written.

## Alternatives represented in the prototype

- **Lifecycle Ring** — recommended. All eight stages remain visible while the
  selected stage and matching WhatsApp preview advance in a pausable loop.
- **Guided Journey** — linear alternative. The full eight-stage rail, spatial charger
  path, next-action explanation and switchable dashboard/WhatsApp preview are
  visible in one coherent website section.
- **System Map** — a simpler alternative that groups the workflow into four large
  phases and is strongest for homepage comprehension, but provides less immediate
  detail than Guided Journey.

## Approval record

- 2026-11-23: owner approved freezing the RushX Lifecycle Ring animation and
  requested removal of the separate “Every stage explained in plain language”
  section. The design is ready for implementation task planning; implementation,
  merge and deployment remain separately gated.
