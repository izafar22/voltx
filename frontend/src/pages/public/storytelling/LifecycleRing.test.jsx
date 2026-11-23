import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { LifecycleRing } from "./LifecycleRing";

jest.mock(
  "react-router-dom",
  () => {
    global.TextEncoder = require("util").TextEncoder;
    global.TextDecoder = require("util").TextDecoder;
    const path = require("path");
    const fs = require("fs");
    const domDirectory = path.dirname(require.resolve("react-router-dom/package.json"));
    const entry = [
      path.join(domDirectory, "node_modules/react-router/dist/development/index.js"),
      path.join(domDirectory, "../react-router/dist/development/index.js"),
    ].find((file) => fs.existsSync(file));
    return require(entry);
  },
  { virtual: true },
);

let container;
let root;
const originalMatchMedia = window.matchMedia;

beforeEach(() => {
  jest.useFakeTimers();
  global.IS_REACT_ACT_ENVIRONMENT = true;
  window.matchMedia = jest.fn(() => ({
    matches: false,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  }));
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root.render(<MemoryRouter><LifecycleRing headingLevel="h1" /></MemoryRouter>);
  });
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  window.matchMedia = originalMatchMedia;
  jest.useRealTimers();
});

const click = (element) => act(() => element.dispatchEvent(new MouseEvent("click", { bubbles: true })));

test("renders eight semantic stages and synchronizes selected detail", () => {
  const stages = [...container.querySelectorAll("[data-stage]")];
  expect(stages).toHaveLength(8);
  expect(stages[0].getAttribute("aria-pressed")).toBe("true");
  click(stages[3]);
  expect(stages[3].getAttribute("aria-pressed")).toBe("true");
  expect(container.querySelector(".rx-lifecycle-detail h3").textContent).toBe("Estimate ready");
  expect(container.textContent).toContain("Approve");
  expect(container.textContent).toContain("Demonstration only");
});

test("auto-advances, explicit pause wins, and next/previous wrap", () => {
  act(() => jest.advanceTimersByTime(3600));
  expect(container.querySelector('[data-stage="accepted"]').getAttribute("aria-pressed")).toBe("true");
  const pause = [...container.querySelectorAll("button")].find((button) => button.textContent.includes("Pause loop"));
  click(pause);
  act(() => jest.advanceTimersByTime(7200));
  expect(container.querySelector('[data-stage="accepted"]').getAttribute("aria-pressed")).toBe("true");
  expect(pause.getAttribute("aria-pressed")).toBe("true");
  click(container.querySelector('[aria-label="Previous lifecycle stage"]'));
  expect(container.querySelector('[data-stage="request"]').getAttribute("aria-pressed")).toBe("true");
  click(container.querySelector('[aria-label="Previous lifecycle stage"]'));
  expect(container.querySelector('[data-stage="returned"]').getAttribute("aria-pressed")).toBe("true");
});

test("reduced motion prevents automatic advancement", () => {
  act(() => root.unmount());
  window.matchMedia = jest.fn(() => ({
    matches: true,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  }));
  root = createRoot(container);
  act(() => root.render(<MemoryRouter><LifecycleRing /></MemoryRouter>));
  act(() => jest.advanceTimersByTime(10800));
  expect(container.querySelector('[data-stage="request"]').getAttribute("aria-pressed")).toBe("true");
});
