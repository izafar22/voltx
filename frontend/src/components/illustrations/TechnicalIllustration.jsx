import "./TechnicalIllustration.css";
const base = "/assets/illustrations";
export const technicalAssets = {
  hero: {
    file: "charger-control-assessment",
    alt: "Conceptual AC wallbox charger beside a control circuit board, illustrating equipment assessment.",
  },
  pcb: {
    file: "pcb-control-board",
    alt: "Conceptual charger control circuit board with relays, capacitors and terminal connectors.",
  },
  ac: {
    file: "ac-wallbox-charger",
    alt: "Generic AC wallbox charger with a neatly looped cable and charging connector.",
  },
  dc: {
    file: "dc-charging-cabinet",
    alt: "Generic floor-standing DC charging cabinet with a side cable and charging handle.",
  },
  power: {
    file: "auxiliary-power-electronics",
    alt: "Conceptual auxiliary power supply beside a heatsink-equipped power electronics module.",
  },
  about: {
    file: "repair-first-assessment",
    alt: "Conceptual charger and detached circuit board with a magnifying lens, representing assessment before a repair decision.",
  },
};
export function TechnicalIllustration({
  asset,
  priority = false,
  decorative = false,
  sizes = "(max-width: 760px) calc(100vw - 44px), 360px",
  className = "",
}) {
  const item = technicalAssets[asset];
  if (!item) return null;
  const widths = asset === "hero" ? [480, 960, 1440] : [480, 960];
  return (
    <img
      className={`rx-technical-image ${className}`}
      src={`${base}/${item.file}-960.webp`}
      srcSet={widths
        .map((width) => `${base}/${item.file}-${width}.webp ${width}w`)
        .join(", ")}
      sizes={sizes}
      width="1440"
      height="960"
      alt={decorative ? "" : item.alt}
      loading={priority ? "eager" : "lazy"}
      fetchpriority={priority ? "high" : undefined}
      decoding="async"
    />
  );
}
