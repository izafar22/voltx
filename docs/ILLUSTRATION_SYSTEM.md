# RushX technical illustration system

Issue #19 extends the unified design system from issue #17 / PR #18. This branch is stacked on `feature/rushx-unified-design-system`, which depends on public education PR #14. Resolve that stack and coordinate the overlapping Storybook foundation in PR #16 before merging. This work does not include OTP PR #12 or change authentication, repair APIs, tracking, WhatsApp, routes or production configuration.

## Art direction and provenance

Six original raster compositions were created with the built-in OpenAI image-generation tool on 2026-11-04, using transparent-background generation. The homepage composition was the visual reference for the other five. These selected assets are submitted for review in this draft; they are not photographs of RushX equipment, inventory, staff or facilities. The tool did not expose a model version. Exact prompts, style-reference relationships, source dimensions, and asset checksums are recorded in [the asset manifest](illustrations/asset-manifest.json).

The common language is an elevated isometric camera, soft upper-left lighting, quiet shadows, off-white and silver housings, charcoal cables, green circuit boards and restrained green details. Existing RushX semantic tokens control all surrounding surfaces, captions and diagram strokes. Hardware is not recolored with CSS filters. No new brand identity, manufacturer logos, embedded lettering, warranties or supported-model claims are introduced.

Five original inline SVG process diagrams use the same isometric vocabulary with deliberately simpler geometry: enquiry, assessment, inspection/estimate, approved repair/testing, and return/documentation. These are editorial diagrams rather than replacements for the generated hardware artwork. FAQ remains text-led to preserve scanability.

## Placement and accessibility

| Page / asset | Purpose | Accessible treatment |
| --- | --- | --- |
| Homepage / charger-control-assessment | Charger and detached control board; assessment hero | Descriptive conceptual-equipment alt; visible non-guarantee caption |
| Services / pcb-control-board | PCB and control-board assessment | Descriptive board alt |
| Services / ac-wallbox-charger | Generic AC equipment | Descriptive generic charger alt |
| Services / dc-charging-cabinet | Generic DC equipment | Descriptive cabinet alt |
| Services / auxiliary-power-electronics | Supporting power modules | Descriptive module alt |
| About / repair-first-assessment | Assessment before a repair decision | Descriptive conceptual-assessment alt; visible facilities disclaimer |
| How It Works / five process diagrams | Reinforce the existing five steps | Decorative, aria-hidden, non-focusable; adjacent text carries all meaning |

Services explicitly identifies the images as conceptual, not inventory or a supported-model list. Existing acceptance, approval, scope and safety copy remains intact. Layout columns, typography, navigation and CTAs are preserved. The homepage's previous CSS hardware illustration is replaced in its existing hero footprint.

## Delivery and performance

Lossless transparent WebP masters live in `frontend/illustration-sources/`, outside the served public directory. Runtime files live in `frontend/public/assets/illustrations/`. The manifest records SHA-256, dimensions and encoded bytes for every file.

Thirteen responsive variants total **588,652 bytes** across the entire library. Every asset has 480px and 960px variants; the homepage also has 1440px. The hero is 23,370 / 63,642 / 114,360 bytes respectively. All four service images total 79,792 bytes at 480px or 214,514 bytes at 960px. Browsers select one variant per image using `srcSet` and `sizes`; these totals are not a per-page download promise.

All images reserve a 3:2 aspect ratio with intrinsic width/height and use contain sizing to avoid hardware cropping. The hero frame retains the existing 390px desktop / 350px tablet / 330px mobile footprint. Only the homepage hero is eager/high-priority; other hardware is lazy-loaded and asynchronously decoded. Transparent pixels work on both existing light and dark surfaces without duplicate theme downloads. No remote image service or runtime dependency is required.

Encoding uses WebP quality 82 with preserved alpha. Enforced per-file budgets are 65,000 bytes at 480px, 140,000 at 960px and 190,000 at 1440px. The lossless masters are intentionally excluded from runtime delivery.

## Maintenance

From repository root, with Pillow and WebP support installed locally:

```sh
python3 frontend/scripts/optimize-illustrations.py
```

This deterministic local encoding step performs no network calls or generation. It contains the whole composition, preserves transparency, writes variants and updates checksums/byte counts. For artwork revisions, use the recorded prompts and selected hero reference with image generation, inspect the actual outputs, archive a lossless master, then run the encoder. Do not replace artwork with stock or placeholders. Review light/dark and mobile/desktop screenshots before accepting any asset update. Deliberately review budget or baseline changes rather than silently raising limits.

Reusable hardware and journey stories are under `Patterns/Technical Illustrations` in Storybook. Its static directory exposes only the optimized illustration folder.

## Verification

- Frontend: 162 tests passed across 15 suites.
- Production application build and production Storybook build passed.
- Application browser suite: 84 passed, including artwork checks across 320, 375, 768 and 1280px in both themes.
- Storybook browser suite: 127 passed, including all 30 stories in mobile/desktop and both themes.
- Browser checks cover actual image decoding, local responsive sources, intrinsic dimensions, priority/lazy behavior, horizontal overflow, stable heading positions, five process diagrams, and axe WCAG 2 A/AA + 2.1 AA checks.
- Controlled browser checks assert cumulative layout shift at or below 0.02. This is laboratory regression evidence, not a production Core Web Vitals measurement.
- [Before/after screenshot index](illustrations/SCREENSHOTS.md): 32 full-page captures, four pages × two widths × two themes × before/after. Before captures use the exact PR #18 base. Screenshots use production builds, mocked auth responses and blocked external requests; they contain no customer data.

Hardware outputs and integrated page screenshots were visually inspected. Existing service-card screenshot baselines continue to pass. No live Google/OTP/provider, production backend, deployment or production infrastructure checks were performed. Production field performance remains a post-release measurement; the draft still needs human visual/content review and resolution of its PR dependencies.
