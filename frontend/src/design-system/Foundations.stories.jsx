import React from "react";
import {
  Zap,
  Wrench,
  CircuitBoard,
  PlugZap,
  Gauge,
  Cpu,
  ArrowUpRight,
  Check,
  Moon,
  Sun,
} from "lucide-react";
import { Logo } from "../components/Logo";
export default {
  title: "Foundations/Brand",
  parameters: {
    docs: {
      description: {
        component:
          "Existing RushX Zap mark, Manrope body, Outfit headings, IBM Plex Mono identifiers, and green accent. Neutral surfaces are shared by public and authenticated UI. See docs/DESIGN_SYSTEM.md for provenance and review decisions.",
      },
    },
  },
};
export const Colors = {
  render: () => (
    <section className="ds-stack">
      <h1 className="ds-heading">RushX / Color roles</h1>
      <Logo />
      <p className="ds-copy">
        Use roles, not literal colors. The toolbar changes the same ThemeContext
        used by the app.
      </p>
      <div className="ds-grid">
        {[
          "background",
          "foreground",
          "primary",
          "primary-foreground",
          "secondary",
          "muted-foreground",
          "charging",
          "brand-foreground",
          "brand-surface",
          "border",
          "input",
          "ring",
          "destructive",
          "wallet",
        ].map((token) => (
          <div className="ds-swatch" key={token}>
            <div
              className="ds-swatch-color"
              style={{ background: `hsl(var(--${token}))` }}
            />
            <p className="ds-swatch-label">--{token}</p>
          </div>
        ))}
      </div>
    </section>
  ),
};
export const Typography = {
  render: () => (
    <section className="ds-stack">
      <h1 className="ds-heading">Type with purpose</h1>
      <h2 className="font-display text-3xl">Outfit / Repair when possible.</h2>
      <p className="text-base">
        Manrope / A considered next step for your faulty EV charger.
      </p>
      <p className="font-mono">IBM Plex Mono / RX-DEMO-001</p>
      <p className="ds-copy">
        Use one h1 per page, a meaningful heading hierarchy and 16px body text.
        Keep helper text readable; never reduce important terms to decorative
        captions.
      </p>
    </section>
  ),
};
export const Spacing = {
  render: () => (
    <section className="ds-stack">
      <h1 className="ds-heading">Space, shape & hierarchy</h1>
      {[1, 2, 3, 4, 5, 6, 8, 12, 16].map((n) => (
        <div className="ds-row" key={n}>
          <code className="w-32">--space-{n}</code>
          <span className="ds-space" style={{ width: `var(--space-${n})` }} />
        </div>
      ))}
      <div className="ds-preview" style={{ boxShadow: "var(--shadow-card)" }}>
        Card: 1rem radius · semantic border · restrained shadow
      </div>
    </section>
  ),
};
export const Icons = {
  render: () => (
    <section className="ds-stack">
      <h1 className="ds-heading">Lucide / A familiar visual vocabulary</h1>
      <div className="ds-grid">
        {Object.entries({
          Zap,
          Wrench,
          CircuitBoard,
          PlugZap,
          Gauge,
          Cpu,
          ArrowUpRight,
          Check,
          Moon,
          Sun,
        }).map(([name, Icon]) => (
          <div key={name} className="ds-row">
            <Icon aria-hidden="true" size={24} strokeWidth={1.5} />
            <span>{name}</span>
          </div>
        ))}
      </div>
      <p className="ds-copy">
        Use 16–24px icons in controls. Hide decorative icons from assistive
        technology; label every icon-only button.
      </p>
    </section>
  ),
};
