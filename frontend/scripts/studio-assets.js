#!/usr/bin/env node
/* Prepares the static files the server-rendered Studio pages load (backend/services/studio_cms.py):
   1. public/studio/tokens.css: a copy of the canonical src/design-system/tokens.css (one source of truth).
   2. public/studio-blocks.css and .js: refreshed from Studio (https://studio.gcombinator.co/docs/blocks, section 6).
      The committed copies are the fallback: an unreachable Studio or another major version keeps them and
      only warns. This never fails the build. Runs as prebuild/prestart. */
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const pub = path.join(root, "public");
const SCRIPT_MAJOR = 2;
const DOCS = "https://studio.gcombinator.co/docs";

fs.mkdirSync(path.join(pub, "studio"), { recursive: true });
fs.copyFileSync(path.join(root, "src/design-system/tokens.css"), path.join(pub, "studio/tokens.css"));

async function fetchText(name) {
  const res = await fetch(`${DOCS}/${name}`, { signal: AbortSignal.timeout(10000) });
  if (!res.ok) throw new Error(`${name}: HTTP ${res.status}`);
  return res.text();
}

(async () => {
  try {
    const [css, js] = await Promise.all([fetchText("studio-blocks.css"), fetchText("studio-blocks.js")]);
    const major = Number((js.match(/version:\s*(\d+)/) || [])[1]);
    if (major !== SCRIPT_MAJOR) {
      console.warn(`studio-assets: studio-blocks.js is version ${major}, built for ${SCRIPT_MAJOR}; keeping the committed copies`);
      return;
    }
    fs.writeFileSync(path.join(pub, "studio-blocks.css"), css);
    fs.writeFileSync(path.join(pub, "studio-blocks.js"), js);
  } catch (error) {
    console.warn(`studio-assets: keeping the committed studio-blocks files (${error.message})`);
  }
})();
