# RushX visual storytelling — issue #21

## Scope and dependency

`feature/rushx-visual-storytelling` starts at issue #19 / PR #20 (`b8153b1`), on top of issue #17 / PR #18 and public education PR #14. The draft targets `feature/rushx-technical-illustrations` to isolate this redesign. Integrate the stacked dependencies separately when authorized; coordinate PR #16's overlapping Storybook foundation. OTP PR #12 is excluded. No backend, authentication handler, repair workflow, WhatsApp, token, theme provider or production configuration changes are included.

## Editorial decisions

The homepage explains the offering with one diagnostic hero, four concise equipment links, and a distinct instrument workbench introducing assessment and approval. It has one prominent repair CTA. The former mission, full journey, FAQ preview, large coverage block and duplicate final CTA are removed from the homepage.

Services uses four alternating, larger equipment narratives. Each has a relevant image, symptoms, assessment considerations and a qualified assessment link. Safety guidance appears once after the equipment narratives. Per-equipment limitations remain because they inform acceptance; repeated generic safety paragraphs are removed.

How It Works is a five-scene ordered journey: enquiry, acceptance assessment, inspection/quotation and authorization, approved repair/testing, return/documentation. No illustration implies an accepted enquiry, completed repair, passed test, price, certification or warranty. The actual copy, not a fabricated pictured screen, explains the process. One repair CTA is attached to the enquiry step.

About uses a separate exploded-equipment concept to explain looking beyond the enclosure and weighing repair against replacement, followed by three concise principles. It does not repeat the homepage hero, journey or service sections. Its repair link is a compact contextual action rather than a duplicated CTA panel.

Coverage is one shared compact footer section per page, including Delhi NCR/Mumbai, conditional courier enquiries, acceptance and shipping instructions, planned Bengaluru expansion and no nationwide onsite guarantee. The footer retains independent-service disclosure, site identity and the repair route. FAQ content and accordion behavior remain. Existing public navigation, metadata, keyboard menu handling, shared Logo/ThemeToggle, semantic colors, editorial fonts and account-aware links remain.

## Supplied-pack review

The user provided `RushX_Images_For_Codex_v2.zip` locally. Its README is treated as source provenance, not an instruction granting authority beyond the user's request. All twelve individual scenes were opened and visually inspected; the reference contact sheet is review-only and is never served. The pack describes fictional AI-generated scenes, not authentic RushX photography. No identifiable actual customer data or actual facility claim is introduced.

| Supplied image | Decision | Review rationale / use |
| --- | --- | --- |
| hero-diagnostic-workbench.webp | Selected | Plausible conceptual charger probing scene; displayed meter number is neither a quoted price nor a measured RushX result. Explicit local caption identifies equipment and readings as illustrative. Homepage only. |
| exploded-ac-charger.webp | Selected | Conceptual enclosure/board layers; not a technical assembly guide. About only; visible caption states limitations. |
| dc-fast-charger-station.webp | Selected | Distinct cabinet and connectors; generic DC equipment label is consistent with the subject. No claim of RushX inventory or manufacturer authorization. Services only. |
| ac-wallbox.webp | Selected | Generic home wallbox/cable context; no pricing or customer information. Services only. |
| power-electronics.webp | Selected | Plausible heatsink, capacitors and inductors; no diagnostic result or performance claim. Services only. |
| pcb-component-repair.webp | Rejected / replaced | Tip appears to contact the IC body rather than a solder joint. Replacement visibly places the iron at a component-lead solder fillet. |
| diagnostic-testing-lab.webp | Rejected / replaced | Screen lists fabricated passed tests. Replacement has unmarked instruments, blank multimeter display and grid-only oscilloscope. Initial replacement's tiny markings were also rejected and removed in a second generation pass. |
| step-01-enquiry.webp | Rejected / replaced | Garbled fields and fictional branded interface. Replacement uses blank generic input shapes and no readable customer information. |
| step-02-assessment.webp | Composition selected; higher-resolution recreation | Original 297×219 crop looked pixelated in the larger journey layout. Reference-driven recreation retains visual inspection and magnifying lamp, without implying energization or completed testing. |
| step-03-estimate.webp | Rejected / replaced | Invented ₹12,500 estimate and approval UI. Replacement shows a technician/customer consultation with abstract report graphics, no prices or approval status. |
| step-04-repair-test.webp | Composition selected; higher-resolution recreation | Original 292×219 crop looked pixelated when enlarged. Reference-driven recreation shows distinct terminal probing rather than another inspection/consultation composition. |
| step-05-return.webp | Rejected / replaced | Fictional shipping branding and “Repaired & Tested” claim. Replacement shows protective packaging and an unlabelled document folder. |
| reference-contact-sheet.webp | Review only | Never included in runtime assets or rendered on pages. |

“Selected” means accepted by the implementation's visual quality review for the draft, not formal user approval, engineering certification, or evidence that a depicted procedure is safe for a customer to perform. Real assessment and testing capabilities must be confirmed per enquiry. Images are illustrative, not repair instructions.

## Generation and provenance

At the user's explicit request, the five rejected scenes were replaced using the built-in OpenAI image-generation tool, using the corresponding supplied scene as a reference. No CLI/API-key fallback or stock imagery was used. The two undersized journey crops were subsequently recreated from their supplied references after integrated screenshot review exposed visible pixelation. All final outputs were opened and inspected before selection. Generated imagery remains fictional and contains no real RushX staff, premises or customer repairs. The tool did not expose a model version.

Exact initial prompts, references, source dimensions and SHA-256 hashes are recorded in [the asset manifest](visual-storytelling/asset-manifest.json). The testing revision prompt is recorded [separately](visual-storytelling/testing-revision-prompt.txt). Source files are in `frontend/visual-storytelling-sources/`, outside public delivery; only reviewed WebP derivatives are under `frontend/public/assets/visual-storytelling/`. No rejected original scene is shipped in that directory.

## Page mapping

| Asset id | Page | Narrative purpose |
| --- | --- | --- |
| hero | Homepage | Recognizable charger diagnostics, with explicit fictional-reading caption |
| testing | Homepage | Distinct instrument workbench supporting assessment/approval explanation |
| pcb / ac / dc / power | Services | Four distinct electronics/equipment assessment narratives |
| step1 / step2 / step3 / step4 / step5 | How It Works | Five ordered scenes, each used once |
| about | About | Exploded concept supporting repair-versus-replacement mission |

No scene is reused on another public page. The old isometric art remains available to its pre-existing Storybook components for compatibility but is no longer displayed by these public pages. The new `Patterns/Visual Storytelling` story uses the actual responsive image component and selected local assets.

## Responsive delivery and maintenance

`StoryImage` supplies real intrinsic dimensions, native aspect ratio, local `srcSet`/`sizes`, meaningful alt text, asynchronous decode and rounded semantic frames. Only the homepage hero and About's lead scene are eager/high-priority on their respective pages. All other scenes are lazy-loaded. Natural lighting and neutral/green equipment work in both themes; no theme-specific duplicate downloads or recoloring filters are used. No text is overlaid on photographs.

The encoder preserves the entire source composition and uses quality-84 WebP. Widths are capped at the actual source size, with targets 320/640/1280px; it never invents detail through file upscaling. There are 31 responsive variants totaling 1,518,852 bytes across the entire library; a browser selects one size per scene, not the whole library. Per-file budget is 180,000 bytes. At 640px-or-native selection, the homepage images total 77,770 bytes and the four service images total 105,090 bytes. All five journey scenes total 219,326 bytes at 640px or 650,474 bytes at 1280px; these are file totals, not network or field-performance measurements. Supplied equipment crops have limited native resolution (roughly 394–550px), so they are not claimed to provide full retina detail at every desktop pixel density. Higher-resolution originals would improve those retained scenes. The two most undersized journey crops are recreated rather than merely upscaled.

```sh
# From repository root, with Pillow/WebP support installed locally:
python3 frontend/scripts/optimize-storytelling.py
```

This is local encoding only, with no network or generation calls. It updates the manifest and frontend `assets.json` geometry/source metadata. To revise artwork, inspect source content first, update the reviewed master and provenance, run the encoder, then rerun tests and inspect both themes. Do not automatically accept OCR-looking text, a label or a plausible-looking circuit as accurate. The image review is deliberately manual; file-hash tests do not certify technical correctness.

## Verification and remaining review

Frontend tests cover distinct mapping across all four pages, five-step semantics and limitations, intrinsic geometry, priority/lazy behavior, local WebP integrity/checksums and budgets. Browser checks cover actual image decoding, all four widths (320/375/768/1280), both themes, overflow, laboratory layout stability, axe WCAG 2 A/AA and 2.1 AA, one shared coverage section, absence of duplicate CTA panels and existing Google/phone login and repair-route regressions. Live providers are mocked and external requests blocked; this is not evidence of SMS/Google delivery or production backend readiness.

The [screenshot index](visual-storytelling/SCREENSHOTS.md) includes before/after production-build captures for all four pages at 375px and 1280px in light/dark. Before is the PR #20 base. Review includes image composition and legibility, content hierarchy, responsive reading order and theme surfaces. These are local controlled screenshots, not deployed pages. Human visual/content approval, stacked dependency integration and production field-performance measurement remain outstanding. No merge or deployment is authorized by this draft.

Local validation: **166 frontend tests (16 suites), 84 application browser checks, 131 Storybook browser checks** passed. Both application and Storybook production builds passed. Controlled browser checks assert CLS at or below 0.02; production Core Web Vitals remain unmeasured. The final screenshot set contains 32 before/after captures.
