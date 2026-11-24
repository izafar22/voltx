# Repair workflow transparency — requirements

Status: FINAL REQUIREMENTS. Approved by the owner on 2026-11-23. Requirements
only; this document does not
authorize design, implementation, merge, deployment, advertising, analytics
changes, or customer messaging.

Prepared 2026-11-23 for the first Delhi/NCR customer-acquisition phase.

## Customer problem

The website does not currently make RushX's strongest service difference clear
enough: a customer can understand what happens to their charger, make the key
repair decision themselves, follow progress in their RushX account, and receive
important lifecycle updates on WhatsApp after explicitly opting in.

A prospective customer should not have to infer whether RushX has a structured
process or worry that their charger will disappear into an opaque repair shop.
The public website must explain the journey before asking the customer to book.

## Customer outcome

After reading the homepage or How it works page, a prospective Delhi/NCR
customer can answer:

1. How do I submit my charger problem?
2. When may I hand over or send the charger?
3. What happens during inspection and diagnosis?
4. Will RushX repair it without my approval?
5. How do I approve or decline the estimate?
6. How will I know when repair, payment and return milestones occur?
7. Where can I check progress if a WhatsApp message is delayed or unavailable?
8. What happens if the charger cannot be repaired?

The desired action is a qualified repair booking, not an unqualified click or a
promise that every charger can be repaired.

## Audience and geographical scope

- Primary audience: individual and business EV charger owners in Delhi and the
  National Capital Region who have a charger fault and are considering repair.
- Public acquisition copy for this phase must target Delhi/NCR clearly.
- Do not advertise Mumbai, Bengaluru, nationwide onsite service or unrestricted
  pan-India courier repair in this feature.
- The website may explain that logistics or hand-off instructions are confirmed
  after RushX accepts the request for inspection. It must not promise collection,
  doorstep service, a service radius, turnaround time or transport pricing unless
  those facts are separately verified and approved.

## Required public story

The homepage must introduce the structured journey prominently enough that a new
visitor can understand it without first opening an account. The How it works page
must provide the complete explanation. Both experiences must be visual-first:
the primary teaching mechanism is an interactive or creative visual journey,
with concise text supporting the visual rather than a long text-only explanation.

The story must communicate these phases in plain language:

1. **Submit the repair request.** The customer provides charger details, fault
   symptoms, useful photos and the measurements required by the booking form.
2. **RushX reviews the request.** Submission confirms receipt of an enquiry; it
   is not technical acceptance and does not guarantee repairability.
3. **Acceptance for inspection.** Only after explicit RushX acceptance does the
   customer receive the approved hand-off or shipping instructions. Acceptance
   permits inspection, not priced repair work.
4. **Receipt and diagnosis.** RushX records physical receipt, inspects the
   charger and identifies the repair scope where feasible.
5. **Estimate and customer decision.** RushX publishes the estimate before
   repair. The customer may approve or decline it. Where the approved WhatsApp
   action is available, the customer may record that decision from the message;
   the RushX account remains the authoritative fallback.
6. **Approved repair and testing.** RushX performs only the approved work and
   tests within the accepted scope. Do not imply a successful repair before the
   result is recorded.
7. **Repair result and payment.** The customer receives the verified repair
   result and balance position. A payment QR or instruction is shown only when a
   verified positive balance is due. Verified payment receives a separate
   acknowledgement.
8. **Return dispatch.** RushX records the courier and tracking facts when the
   charger is actually dispatched. Do not describe provider acceptance as
   delivery or live tracking.

Not every internal repair status needs to be exposed as a separate marketing
step. The presentation may group related statuses, provided it preserves the
decision boundaries and does not misstate when events occur.

## WhatsApp transparency promise

WhatsApp must be presented as optional, consent-based milestone communication,
not continuous GPS-style tracking, guaranteed delivery, a general chat inbox, or
the only way to follow a repair.

The website must explain that:

- the customer explicitly enables WhatsApp updates for the individual repair;
- signing in with WhatsApp does not automatically enable lifecycle updates;
- messages go only to the customer's eligible verified account number;
- the RushX account remains the reliable place to review current repair status;
- the customer may stop future WhatsApp updates from repair details; and
- provider or network delays can occur without changing the underlying repair.

The public journey may summarize the eight implemented customer messages:

1. request received;
2. accepted for inspection with hand-off/shipping instructions;
3. charger received by RushX;
4. estimate ready with the customer decision action;
5. estimate approval recorded;
6. repair result with the verified balance position;
7. verified payment received; and
8. charger dispatched back to the customer.

Exception states such as declined estimate, not repairable, cancelled or delayed
work remain visible through the account/support journey unless a separately
approved message exists. The public page must not imply that every exception
generates a WhatsApp message.

## Visual and interactive journey requirements

The main journey must help a visitor understand the process by seeing it unfold.
The detailed design is a later approval gate, but it must satisfy these functional
requirements:

- Present a recognizable charger moving through the RushX lifecycle between the
  customer, RushX inspection/repair and return, rather than relying on a numbered
  text list alone.
- Let the visitor select or advance through grouped repair phases. Hover-only
  interaction is not sufficient; controls must work with touch and keyboard.
- Visually distinguish the three critical decision boundaries: RushX accepts the
  charger for inspection, the customer approves or declines the estimate, and
  verified payment/return follows the recorded repair result.
- Pair applicable stages with a creative WhatsApp-style message preview so the
  visitor understands what an update contains and why it arrives.
- Make the estimate stage visibly interactive in the explanation: the example may
  show Approve and Decline controls, but these must be clearly presented as a
  non-functional demonstration and must never invoke a real repair action.
- Show that the RushX dashboard and WhatsApp work together: the account holds the
  authoritative repair state, while WhatsApp brings selected milestones to the
  customer.
- Use progressive disclosure. The first view should communicate the complete
  journey at a glance; selecting a stage may reveal its short explanation,
  message preview and customer action.
- Keep the homepage version concise, using a strong visual overview and a clear
  route to the complete interactive How it works experience.
- Motion may reinforce direction and progress but must not be required for
  comprehension. Respect reduced-motion preferences and avoid auto-advancing
  content that a visitor cannot pause.
- Creative images or illustrations must follow the established RushX identity.
  They must not falsely depict a real RushX employee, facility, customer repair,
  diagnostic result, manufacturer relationship or certification.
- Do not use a customer screenshot or a real WhatsApp conversation. Message
  previews must use fictional, generic data and match the meaning of the approved
  lifecycle templates without exposing personal information.

The visual should make these concepts understandable even before all supporting
copy is read: where the charger is, who acts next, what has been verified, and
which milestone update the customer receives.

## Visual quality and system-confidence requirements

The experience must feel deliberately designed and operationally credible, not
like a decorative timeline added to a marketing page. It should give a customer
confidence that RushX has a thoughtful system for handling their charger and
communicating important decisions.

- Create one cohesive visual system connecting the charger journey, RushX status
  states, customer actions, dashboard and WhatsApp previews.
- Use the established RushX logo, editorial typography, green accent, light/dark
  themes and design tokens. Do not substitute or reinterpret the logo.
- Give the journey a strong visual centrepiece suitable for the homepage rather
  than presenting eight equal text cards with no hierarchy.
- Use clear progress, completed, current, decision and upcoming states. Each state
  needs an icon, label or shape in addition to colour.
- Make customer-control moments visually prominent: inspection acceptance,
  estimate approval/decline, payment due only when verified, and return dispatch.
- Use purposeful transitions such as a progress path, charger movement, status
  confirmation and message arrival. Motion should reinforce the workflow rather
  than exist as decoration.
- WhatsApp previews should feel familiar and polished while remaining clearly
  illustrative, using generic fictional content and no copied proprietary app
  interface beyond what is necessary to communicate a message and action.
- Show operational reassurance through truthful interface cues such as recorded
  milestones, timestamps described as examples, verified-event indicators and a
  visible dashboard fallback. Do not invent live technician tracking, response
  times, success rates or service guarantees.
- Keep the composition spacious, premium and easy to scan. Avoid visual clutter,
  excessive badges, dense paragraphs, novelty animation or an appearance similar
  to an internal admin screen.
- The mobile experience must feel intentionally composed, not merely a compressed
  desktop timeline. Stage controls, previews and calls to action must remain clear
  and comfortable to use on a phone.
- The final design must be reviewed at the agreed viewport sizes in both themes
  before implementation approval. A static or interactive preview should show the
  homepage overview, complete journey, selected stage and WhatsApp preview states.

Visual polish must support an accurate perception: RushX has a structured repair
workflow and customer communication system. It must not create a false perception
of automation, tracking precision, staffing, facilities or outcomes beyond the
implemented product.

## 3D, WebGL and creative-technology requirements

The approved design may use Blender-authored assets, Three.js, React Three Fiber,
WebGL or another suitable browser graphics approach when it materially improves
customer understanding. The technology choice remains a design and technical
review decision; this requirements approval does not add a runtime dependency.

A preferred creative direction to explore is a stylized RushX repair system in
which a recognizable EV charger travels through distinct visual stations:

- customer request and RushX review;
- accepted hand-off for inspection;
- receipt and diagnosis;
- estimate presented for the customer's decision;
- approved component-level repair and testing;
- verified balance and payment acknowledgement; and
- packed return dispatch.

Selecting a station may focus the scene, reveal the customer action, synchronize
the matching dashboard state and introduce the illustrative WhatsApp update. The
experience should communicate a connected operating system rather than a literal
depiction of RushX premises or an automated factory.

Any 3D or WebGL design must meet these constraints:

- No framework or rendering library may be selected solely for novelty. Compare
  the proposed 3D solution with a lighter CSS/SVG/canvas alternative during design.
- Keep the initial public page useful before the interactive scene loads. The page
  heading, core promise and primary booking action must not depend on WebGL.
- Load the interactive scene progressively and avoid delaying meaningful content,
  navigation or the primary call to action.
- Optimize models, meshes, materials, textures, lighting and animation for mobile
  browsers. Define and verify explicit asset and performance budgets during design.
- Provide a polished static or lightweight two-dimensional fallback for unsupported
  WebGL, low-performance devices, data-saving conditions, reduced motion and load
  failure. The fallback must explain the same journey and offer the same links.
- Avoid forced camera movement, scroll hijacking, flashing, excessive parallax or
  uncontrolled auto-rotation. Visitors must remain in control of navigation.
- All stage selection and information must remain available through semantic HTML,
  touch and keyboard controls outside the canvas. Canvas hit targets alone are not
  sufficient.
- Announce selected-stage changes appropriately without exposing decorative scene
  objects to assistive technology.
- Pause or reduce rendering when the scene is off-screen, the tab is hidden or the
  visitor requests reduced motion. Do not consume continuous GPU resources without
  customer value.
- Avoid device fingerprinting, camera/microphone access, third-party tracking or
  external asset hosts introduced solely by the visualization.
- Test representative Android phones as well as the agreed responsive browser
  widths. A visually impressive desktop scene with a poor mobile experience is not
  acceptable.
- Keep the visual fictional and brand-led. Do not reconstruct a real customer
  charger, RushX facility, technician or WhatsApp conversation without separately
  verified rights and consent.

The design review must include at least one creative visual concept and one
performance-safe fallback, with a recommendation explaining why the chosen medium
best communicates the workflow.

## Trust and truthfulness requirements

- Preserve the approved RushX logo and established visual identity.
- State that RushX is an independent, multi-brand repair service and does not
  claim manufacturer authorization.
- Do not guarantee acceptance, repair success, parts availability, turnaround
  time, savings, warranty, pickup, delivery or a particular diagnosis.
- Explain that the customer controls the priced repair decision.
- Do not claim fictional or AI-generated imagery shows real RushX technicians,
  facilities, customer chargers or completed repairs.
- Do not publish customer names, phone numbers, addresses, repair references,
  WhatsApp screenshots or case results without separately verified consent.
- Use “RushX” in customer-facing copy; internal or legacy product names must not
  appear in the journey.

## Calls to action and conversion

- Primary call to action: **Book a repair** or **Request an assessment**, linking
  to the existing repair-booking route.
- Secondary call to action: **Track a repair**, linking to the existing account
  journey.
- The homepage explanation must offer a clear route to the full How it works page.
- Calls to action must not bypass authentication, consent, eligibility or the
  existing repair request workflow.
- No new phone number, WhatsApp click-to-chat destination, lead form, payment
  route or advertising tracker is introduced by this requirement.

## Search and content requirements

- Page titles and descriptions must describe EV charger repair in Delhi/NCR and
  the transparent repair process naturally, without keyword stuffing.
- The How it works page must have one clear page heading and semantically ordered
  sections suitable for search engines and assistive technology.
- Copy must distinguish a repair enquiry from accepted inspection and accepted
  inspection from customer-approved repair.
- Structured data, new location pages, brand pages, case studies and paid-search
  landing pages are outside this feature and require their own evidence and
  review.

## Experience and accessibility

- The explanation must work at 320, 375, 768 and 1280 pixel widths and in both
  supported themes.
- The visual journey must include an equivalent semantic structure and concise
  text so it remains understandable when images, motion or client-side interaction
  are unavailable. Do not rely on colour alone to communicate state.
- Headings, lists and links must be semantic; keyboard focus and visible labels
  must follow the existing public-page patterns.
- Interactive stages must expose the selected state to assistive technology, keep
  a logical focus order and provide controls large enough for touch use.
- Avoid an overly long wall of text on the homepage. Use a concise overview there
  and reserve detailed conditions for How it works and the FAQ.
- Existing navigation, logo, authentication, repair booking, floating WhatsApp
  support link, policy pages and protected customer routes must continue working.

## Out of scope

- Changing the repair state machine, estimate approval logic, payment workflow,
  WhatsApp templates, worker, consent model or provider configuration.
- Sending test or production WhatsApp messages.
- New pickup, courier, logistics, warranty, pricing or turnaround commitments.
- Google Ads, Google Business Profile, analytics installation, call tracking,
  SEO location/brand pages, testimonials or review collection.
- Production deployment or modification of live customer data.

## Acceptance criteria

1. A new visitor can describe the journey from request through return after
   reading the public explanation.
2. Homepage copy communicates structured repair, customer estimate approval and
   optional WhatsApp milestone updates through a concise visual overview without
   becoming a full policy page.
3. How it works accurately covers request review, explicit inspection acceptance,
   receipt, diagnosis, estimate decision, approved repair/testing, verified
   payment position and return dispatch.
4. The eight implemented WhatsApp messages are represented accurately, with the
   RushX account identified as the status fallback and exceptions not overstated.
5. Public acquisition copy for this phase targets Delhi/NCR and removes claims
   that market Mumbai, Bengaluru, nationwide onsite service or unrestricted
   pan-India repair.
6. Every acceptance, repair, payment, dispatch and delivery statement is tied to
   the correct verified event and avoids guarantees.
7. Primary booking, full-process and repair-tracking links point to existing
   routes and retain existing security and consent boundaries.
8. Automated tests cover required copy/links and prevent regression to misleading
   geography or lifecycle claims.
9. The complete visual journey is operable by touch and keyboard, honors reduced
   motion, has an equivalent semantic reading order, and uses only fictional,
   non-personal message examples.
10. The approved design demonstrates a polished, cohesive RushX system across the
    homepage overview, selected lifecycle stages, dashboard relationship and
    WhatsApp previews at mobile and desktop sizes in both themes.
11. If 3D/WebGL is selected, the experience loads progressively, stays usable
    without WebGL, respects reduced motion, remains controllable by semantic HTML,
    and meets the design-approved mobile performance and asset budgets.
12. Relevant frontend unit, build, browser and Storybook checks pass, and the PR
   records tests, risks, rollback and context-documentation changes.
13. Design, implementation, merge and deployment each remain separate approval
    gates after these requirements are approved.

## Approved decisions

1. Delhi/NCR is the only geography marketed in this phase, while the exact
   collection/hand-off method remains subject to RushX acceptance.
2. The public site describes all eight WhatsApp milestones, with a shorter grouped
   visual overview on the homepage and the complete interactive journey on How it
   works.
3. “Book a repair” remains the primary conversion action and “Track a repair” the
   secondary action.
4. The design may use Blender-authored assets, Three.js, React Three Fiber, WebGL
   or another suitable creative technology, subject to the performance,
   accessibility, fallback and truthfulness requirements above.
5. The design should feel visually attractive, modern and operationally credible,
   demonstrating RushX's structured system without overstating its capabilities.

## Approval record

- 2026-11-23: owner requested that the website explain the structured repair
  workflow and lifecycle transparency to prospective Delhi/NCR customers.
- 2026-11-23: owner required a visual-first, interactive or creative-image
  experience rather than a primarily textual explanation.
- 2026-11-23: owner requested a visually attractive system presentation and
  authorized exploration of Blender, Three.js, WebGL and other suitable 3D web
  technologies.
- 2026-11-23: owner explicitly approved this requirements document. Visual design,
  implementation task plan, implementation, merge and deployment remain separate
  approval gates.
