import React from "react";
import { MemoryRouter } from "react-router-dom";
import { useGlobals } from "storybook/preview-api";
import { ThemeProvider } from "../src/context/ThemeContext";
import "../src/index.css";
import "../src/pages/public/PublicPage.css";
import "../src/design-system/stories.css";

// Stories must never access application APIs or third-party endpoints.
const originalFetch = window.fetch.bind(window);
window.fetch = (input, init) => {
  const url = new URL(
    typeof input === "string" || input instanceof URL ? input : input.url,
    location.href,
  );
  if (url.origin !== location.origin || url.pathname.startsWith("/api/"))
    return Promise.reject(
      new Error("Live network is disabled in RushX Storybook."),
    );
  return originalFetch(input, init);
};
const originalOpen = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function (method, target, ...args) {
  const url = new URL(target, location.href);
  if (url.origin !== location.origin || url.pathname.startsWith("/api/"))
    throw new Error("Live network is disabled in RushX Storybook.");
  return originalOpen.call(this, method, target, ...args);
};
function withRushX(Story) {
  const [globals, updateGlobals] = useGlobals();
  return (
    <ThemeProvider
      theme={globals.theme}
      onThemeChange={(theme) => updateGlobals({ theme })}
    >
      <MemoryRouter>
        <main className="ds-canvas">
          <Story />
        </main>
      </MemoryRouter>
    </ThemeProvider>
  );
}
export default {
  decorators: [withRushX],
  tags: ["autodocs"],
  globalTypes: {
    theme: {
      description: "RushX theme (shared ThemeContext)",
      toolbar: {
        title: "Theme",
        icon: "circlehollow",
        items: ["light", "dark"],
        dynamicTitle: true,
      },
    },
  },
  // Playwright owns automated axe scans; avoid a concurrent addon engine.
  initialGlobals: { theme: "light", a11y: { manual: true } },
  parameters: {
    layout: "fullscreen",
    options: {
      storySort: { order: ["Foundations", "Components", "Patterns"] },
    },
    controls: { expanded: true },
    backgrounds: { disable: true }, // Canvas background is always the app's semantic surface.
    viewport: {
      options: {
        mobile320: {
          name: "Mobile 320",
          styles: { width: "320px", height: "900px" },
        },
        mobile375: {
          name: "Mobile 375",
          styles: { width: "375px", height: "900px" },
        },
        tablet: {
          name: "Tablet 768",
          styles: { width: "768px", height: "1024px" },
        },
        desktop: {
          name: "Desktop 1280",
          styles: { width: "1280px", height: "900px" },
        },
      },
    },
    a11y: { test: "error" },
    docs: { toc: true },
  },
};
