import { addons } from "storybook/manager-api";
import { create } from "storybook/theming";
addons.setConfig({
  theme: create({
    base: "light",
    brandTitle: "RushX / Design System",
    colorPrimary: "#00c759",
    colorSecondary: "#14753e",
  }),
});
