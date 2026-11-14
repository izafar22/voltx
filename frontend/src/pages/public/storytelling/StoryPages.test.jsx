import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import fs from "fs";
import path from "path";
import crypto from "crypto";
import {
  HomeStory,
  ServicesStory,
  JourneyStory,
  AboutStory,
} from "./StoryPages";
import { storyAssets } from "./StoryImage";
// Jest 27 does not resolve this package's exports map. Resolve its CJS entry to
// exercise the installed, real router (including browser history and redirects).
jest.mock(
  "react-router-dom",
  () => {
    global.TextEncoder = require("util").TextEncoder;
    global.TextDecoder = require("util").TextDecoder;
    const path = require("path");
    const fs = require("fs");
    const domDirectory = path.dirname(
      require.resolve("react-router-dom/package.json"),
    );
    // npm may nest react-router under react-router-dom or hoist it.
    const entry = [
      path.join(
        domDirectory,
        "node_modules/react-router/dist/development/index.js",
      ),
      path.join(domDirectory, "../react-router/dist/development/index.js"),
    ].find((file) => fs.existsSync(file));
    return require(entry);
  },
  { virtual: true },
);
let el, root;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  el = document.createElement("div");
  document.body.appendChild(el);
  root = createRoot(el);
});
afterEach(() => {
  act(() => root.unmount());
  el.remove();
});
function render(Component) {
  act(() =>
    root.render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Component />
      </MemoryRouter>,
    ),
  );
}
test("all four narratives use distinct assets, real routes, and one page heading", () => {
  const used = [];
  for (const Page of [HomeStory, ServicesStory, JourneyStory, AboutStory]) {
    render(Page);
    expect(el.querySelectorAll("h1")).toHaveLength(1);
    for (const figure of el.querySelectorAll("[data-story-asset]"))
      used.push(figure.dataset.storyAsset);
    for (const a of el.querySelectorAll("a.rx-button"))
      expect(a.getAttribute("href")).toBe("/repairs/new");
    expect(el.querySelectorAll(".rx-final")).toHaveLength(0);
  }
  expect(used).toHaveLength(12);
  expect(new Set(used).size).toBe(12);
});
test("only homepage hero and About lead are eager; all scenes reserve geometry and have meaningful alt", () => {
  for (const Page of [HomeStory, ServicesStory, JourneyStory, AboutStory]) {
    render(Page);
    for (const figure of el.querySelectorAll("[data-story-asset]")) {
      const image = figure.querySelector("img"),
        id = figure.dataset.storyAsset;
      expect(image.alt.length).toBeGreaterThan(30);
      expect(Number(image.width)).toBeGreaterThan(0);
      expect(Number(image.height)).toBeGreaterThan(0);
      expect(image.getAttribute("srcset")).toContain("w");
      expect(image.getAttribute("loading")).toBe(
        ["hero", "about"].includes(id) ? "eager" : "lazy",
      );
    }
  }
});
test("five journey steps retain acceptance, approval, safe shipping and quotation limitations", () => {
  render(JourneyStory);
  expect(el.querySelectorAll("ol > li")).toHaveLength(5);
  for (const text of [
    "technical acceptance",
    "authorize",
    "Warranty terms",
    "shipping instructions",
    "Do not open",
  ])
    expect(el.textContent.toLowerCase()).toContain(text.toLowerCase());
  expect(el.textContent).not.toMatch(/₹|12,500|guaranteed repair/i);
});
test("every approved runtime asset matches its review manifest, is local WebP, and stays within budget", () => {
  const manifest = JSON.parse(
    fs.readFileSync(
      path.join(
        process.cwd(),
        "../docs/visual-storytelling/asset-manifest.json",
      ),
      "utf8",
    ),
  );
  expect(manifest.assets).toHaveLength(12);
  for (const asset of manifest.assets) {
    expect(storyAssets[asset.id].outputs).toEqual(asset.outputs);
    for (const output of asset.outputs) {
      expect(output.width).toBeLessThanOrEqual(asset.width);
      const file = fs.readFileSync(
        path.join(process.cwd(), "public", output.src),
      );
      expect(file.toString("ascii", 0, 4)).toBe("RIFF");
      expect(file.toString("ascii", 8, 12)).toBe("WEBP");
      expect(file.length).toBe(output.bytes);
      expect(file.length).toBeLessThanOrEqual(180000);
      expect(crypto.createHash("sha256").update(file).digest("hex")).toBe(
        output.sha256,
      );
    }
  }
});
