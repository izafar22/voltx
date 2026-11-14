import React from "react";
import { Input } from "../components/ui/input";
export default {
  title: "Components/Input",
  component: Input,
  args: { disabled: false, placeholder: "Charger model", type: "text" },
  argTypes: { type: { control: "select", options: ["text", "tel", "email"] } },
  render: (args) => (
    <div className="ds-field">
      <label htmlFor="example-model">Charger model</label>
      <Input {...args} id="example-model" aria-describedby="field-help" />
      <p id="field-help" className="ds-note">
        Use the model printed on the equipment label.
      </p>
    </div>
  ),
};
export const Default = {};
export const Disabled = {
  args: { disabled: true, value: "Example model", readOnly: true },
};
export const Error = {
  render: () => (
    <div className="ds-field">
      <label htmlFor="error-model">Charger model</label>
      <Input
        id="error-model"
        aria-invalid="true"
        aria-describedby="model-error"
      />
      <p id="model-error" className="text-sm text-destructive">
        Enter the model to help us assess compatibility.
      </p>
    </div>
  ),
};
