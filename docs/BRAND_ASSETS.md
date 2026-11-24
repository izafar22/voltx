# RushX canonical logo

Owner-confirmed reference: 2026-11-24.

The canonical RushX identity is:

- a black filled lightning bolt;
- centered inside a bright green (`#00E889`) rounded square;
- followed by the complete **RushX** wordmark in Outfit Bold, using the active
  foreground colour when rendered in the application.

## Authoritative files

- `frontend/src/assets/brand/rushx-mark.svg` is the canonical symbol used by the
  application.
- `frontend/src/assets/brand/rushx-logo.svg` is the portable dark-background
  lockup. Its wordmark remains SVG text so the product name is readable and the
  preferred Outfit font can be used when available.
- `frontend/src/components/Logo.jsx` is the canonical application rendering. Use
  this component in React UI instead of recreating the mark or embedding the
  lockup SVG.

## Usage rules

1. Do not redraw, rotate, outline, recolour or replace the lightning bolt with a
   generic Zap icon.
2. Do not recolour only the `X`, abbreviate the wordmark or change its spelling.
3. Keep the mark square with a corner radius equal to one quarter of its width.
4. Keep the bolt black and the mark background `#00E889`.
5. In application UI, render the wordmark as live Outfit Bold text in the current
   foreground colour so it remains readable in both themes.
6. Preserve at least one quarter of the mark width as clear space around the full
   lockup. Do not place the logo on a competing bright-green surface.

The screenshot supplied by the owner is visual approval of this geometry and
colour relationship. The SVG files are now the source of truth; screenshots are
references, not assets to crop or retrace.
