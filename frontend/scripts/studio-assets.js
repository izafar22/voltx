#!/usr/bin/env node
/* Prepares the static files the server-rendered Studio pages load (backend/services/studio_cms.py).

   Every build (prebuild/prestart):
     public/studio/tokens.css ← src/design-system/tokens.css (one source of truth for the design tokens).

   Only on request, `node scripts/studio-assets.js --refresh`:
     public/studio-blocks.css and .js ← https://studio.gcombinator.co/docs (blocks guide, section 6).
   Builds never download them: the committed copies are what ships, so a change to Studio's script reaches
   the site only through a reviewed commit. Refresh, review the diff, commit. A different major version of
   the script is refused. */
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

async function refresh() {
  const [css, js] = await Promise.all([fetchText("studio-blocks.css"), fetchText("studio-blocks.js")]);
  const major = Number((js.match(/version:\s*(\d+)/) || [])[1]);
  if (major !== SCRIPT_MAJOR) {
    throw new Error(`studio-blocks.js is version ${major}; this site is built for ${SCRIPT_MAJOR}. Read the blocks guide's Changes first.`);
  }
  fs.writeFileSync(path.join(pub, "studio-blocks.css"), css);
  fs.writeFileSync(path.join(pub, "studio-blocks.js"), js);
  console.log("studio-assets: refreshed public/studio-blocks.css and .js; review the diff before committing");
}

if (process.argv.includes("--refresh")) {
  refresh().catch((error) => {
    console.error(`studio-assets: ${error.message}`);
    process.exitCode = 1;
  });
}
