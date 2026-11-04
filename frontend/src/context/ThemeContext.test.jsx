import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { ThemeProvider, useTheme } from "./ThemeContext";
let root, container;
const originalMatchMedia = window.matchMedia;
function Probe() {
  const { theme, toggle } = useTheme();
  return <button onClick={toggle}>{theme}</button>;
}
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  localStorage.clear();
  window.matchMedia = jest.fn(() => ({ matches: false }));
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => {
  act(() => root.unmount());
  container.remove();
  localStorage.clear();
  window.matchMedia = originalMatchMedia;
  document.documentElement.classList.remove("dark");
  document.documentElement.style.colorScheme = "";
  jest.restoreAllMocks();
});
const render = (props) =>
  act(() =>
    root.render(
      <React.StrictMode>
        <ThemeProvider {...props}>
          <Probe />
        </ThemeProvider>
      </React.StrictMode>,
    ),
  );
test("persisted dark mode drives both the root class and native color scheme", () => {
  localStorage.setItem("rushx-theme", "dark");
  render();
  expect(container.textContent).toBe("dark");
  expect(document.documentElement.classList.contains("dark")).toBe(true);
  expect(document.documentElement.style.colorScheme).toBe("dark");
  act(() => container.querySelector("button").click());
  expect(localStorage.getItem("rushx-theme")).toBe("light");
  expect(document.documentElement.classList.contains("dark")).toBe(false);
});
test("invalid stored value falls back to system preference", () => {
  localStorage.setItem("rushx-theme", "unexpected");
  window.matchMedia = jest.fn(() => ({ matches: true }));
  render();
  expect(container.textContent).toBe("dark");
  expect(localStorage.getItem("rushx-theme")).toBe("dark");
});
test("theme remains usable when persistence is blocked", () => {
  jest.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  jest.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  render();
  act(() => container.querySelector("button").click());
  expect(container.textContent).toBe("dark");
});
test("controlled Storybook theme shares the provider and reports toggles", () => {
  const onThemeChange = jest.fn();
  render({ theme: "dark", onThemeChange });
  act(() => container.querySelector("button").click());
  expect(onThemeChange).toHaveBeenCalledWith("light");
  render({ theme: "light", onThemeChange });
  expect(document.documentElement.style.colorScheme).toBe("light");
});
test("preference syncs when another tab changes storage", () => {
  render();
  act(() =>
    window.dispatchEvent(
      new StorageEvent("storage", { key: "rushx-theme", newValue: "dark" }),
    ),
  );
  expect(container.textContent).toBe("dark");
});
