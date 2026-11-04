import React from "react";
import { Loader2 } from "lucide-react";
import { Button } from "../components/ui/button";
export default {
  title: "Components/Button",
  component: Button,
  args: {
    children: "Request an assessment",
    variant: "default",
    size: "default",
    disabled: false,
  },
  argTypes: {
    variant: {
      control: "select",
      options: [
        "default",
        "outline",
        "secondary",
        "ghost",
        "link",
        "destructive",
      ],
    },
    size: { control: "select", options: ["default", "sm", "lg", "icon"] },
    asChild: { table: { disable: true } },
  },
  parameters: {
    docs: {
      description: {
        component:
          "Use primary for the next action, outline for alternatives, destructive only for irreversible actions. Prefer a link via asChild for navigation. Minimum 44px controls; keyboard focus and real hover can be reviewed in canvas.",
      },
    },
  },
};
export const Primary = {};
export const Outline = { args: { variant: "outline" } };
export const Disabled = { args: { disabled: true } };
export const Loading = {
  args: {
    disabled: true,
    "aria-busy": true,
    children: (
      <>
        <Loader2 className="animate-spin" aria-hidden="true" />
        Requesting assessment…
      </>
    ),
  },
};
export const Destructive = {
  args: { variant: "destructive", children: "Cancel request" },
};
export const Variants = {
  render: () => (
    <section className="ds-stack">
      <h1 className="ds-heading">Action hierarchy</h1>
      <div className="ds-row">
        {[
          "default",
          "outline",
          "secondary",
          "ghost",
          "link",
          "destructive",
        ].map((variant) => (
          <Button key={variant} variant={variant}>
            {variant}
          </Button>
        ))}
      </div>
      <p className="ds-note">
        Tab to inspect focus. Hover a button to inspect its real interaction
        state.
      </p>
    </section>
  ),
};
