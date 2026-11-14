import React, { act } from "react";
import { createRoot } from "react-dom/client";
import fs from "fs";
import path from "path";
import crypto from "crypto";
import {
  TechnicalIllustration,
  technicalAssets,
} from "./TechnicalIllustration";
import { ProcessIllustration } from "./ProcessIllustration";
let container, root;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => {
  act(() => root.unmount());
  container.remove();
});
test("hero reserves geometry, has descriptive alt text and high-priority responsive sources", () => {
  act(() => root.render(<TechnicalIllustration asset="hero" priority />));
  const img = container.querySelector("img");
  expect(img.alt).toMatch(/Conceptual AC wallbox/);
  expect(img.getAttribute("loading")).toBe("eager");
  expect(img.getAttribute("fetchpriority")).toBe("high");
  expect(img.getAttribute("width")).toBe("1440");
  expect(img.getAttribute("height")).toBe("960");
  expect(img.getAttribute("srcset")).toContain("1440w");
  expect(img.getAttribute("sizes")).toBeTruthy();
});
test("contextual hardware stays lazy and a decorative usage is silent to screen readers", () => {
  act(() => root.render(<TechnicalIllustration asset="pcb" />));
  let img = container.querySelector("img");
  expect(img.alt).toMatch(/control circuit board/);
  expect(img.getAttribute("loading")).toBe("lazy");
  expect(img.hasAttribute("fetchpriority")).toBe(false);
  act(() => root.render(<TechnicalIllustration asset="pcb" decorative />));
  img = container.querySelector("img");
  expect(img.alt).toBe("");
});
test("all selected assets and responsive files are real, local, versioned and within budgets", () => {
  const manifest = JSON.parse(
    fs.readFileSync(
      path.join(process.cwd(), "../docs/illustrations/asset-manifest.json"),
      "utf8",
    ),
  );
  expect(manifest.assets).toHaveLength(6);
  for (const asset of manifest.assets) {
    expect(asset.file).toBe(technicalAssets[asset.id].file);
    expect(technicalAssets[asset.id].alt.length).toBeGreaterThan(30);
    for (const output of asset.outputs) {
      const bytes = fs.readFileSync(
        path.join(process.cwd(), "..", output.file),
      );
      expect(bytes.toString("ascii", 0, 4)).toBe("RIFF");
      expect(bytes.toString("ascii", 8, 12)).toBe("WEBP");
      expect(bytes.length).toBe(output.bytes);
      expect(crypto.createHash("sha256").update(bytes).digest("hex")).toBe(
        output.sha256,
      );
      expect(bytes.length).toBeLessThanOrEqual(
        output.width === 1440 ? 190000 : output.width === 960 ? 140000 : 65000,
      );
    }
  }
});
test("five original process diagrams are decorative alongside the real step text", () => {
  act(() =>
    root.render(
      <div>
        {[0, 1, 2, 3, 4].map((step) => (
          <ProcessIllustration key={step} step={step} />
        ))}
      </div>,
    ),
  );
  const svgs = container.querySelectorAll("svg");
  expect(svgs).toHaveLength(5);
  for (const svg of svgs) {
    expect(svg.getAttribute("aria-hidden")).toBe("true");
    expect(svg.getAttribute("viewBox")).toBe("0 0 160 112");
    expect(svg.getAttribute("height")).toBe("112");
  }
});
