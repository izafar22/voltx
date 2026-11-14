import React from "react";
import { TechnicalIllustration } from "../components/illustrations/TechnicalIllustration";
import { ProcessIllustration } from "../components/illustrations/ProcessIllustration";
import { RepairJourney } from "../components/patterns/RepairPatterns";
import { steps } from "../pages/public/content";
export default {
  title: "Patterns/Technical Illustrations",
  parameters: {
    docs: {
      description: {
        component:
          "Original generated conceptual equipment, not actual RushX inventory or supported models. Neutral materials and RushX green share a consistent isometric family; transparent WebP assets sit on semantic surfaces. Five original token-aware SVG diagrams support the real enquiry-to-return journey.",
      },
    },
  },
};
export const Hardware = {
  args: { asset: "hero", decorative: false },
  argTypes: {
    asset: {
      control: "select",
      options: ["hero", "pcb", "ac", "dc", "power", "about"],
    },
    decorative: { control: "boolean" },
  },
  render: (args) => (
    <figure className="rx-technical-hero max-w-xl">
      <TechnicalIllustration {...args} />
      <figcaption className="rx-art-caption">
        Conceptual hardware; technical acceptance is required.
      </figcaption>
    </figure>
  ),
};
export const Journey = {
  render: () => (
    <section className="rx-public">
      <h2 className="ds-heading">From enquiry to return</h2>
      <RepairJourney
        steps={steps}
        illustrations={steps.map((_, step) => (
          <ProcessIllustration key={step} step={step} />
        ))}
      />
    </section>
  ),
};
