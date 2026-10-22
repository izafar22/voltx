# Dependency security triage — PR #4, 2026-10-22

Review comment 6336573688; baseline `4ae54c8`. No merge or deployment authorized.

## Installer and audit reconciliation

`frontend/package.json` declares Yarn 1.22.22, including its integrity hash. The
validated graph is `yarn.lock` plus the existing Yarn `resolutions`. Node 22.22.0,
npm 10.9.4, and Yarn 1.22.22 were used. A fresh isolated copy of tracked frontend
files was installed; the developer's shared node_modules and environment were not
modified. Install scripts were disabled. A final frozen install also passed.

There is no checked-in deployment manifest proving the actual production installer.
Confirm production uses the declared frozen Yarn graph before release. The retained
npm lockfile predates these fixes; **npm installs are not validated or release-ready**.
It was deliberately neither removed nor regenerated with npm, which ignores Yarn
resolutions. This is not a package-manager migration. A deployment using npm needs
its own reviewed compatible graph and tests; the Yarn findings cannot clear it.

`npm audit --json` still reports **116 vulnerable package entries: 2 critical,
73 high, 35 moderate, 6 low** from package-lock.json. Its critical packages are
proxy-addr and shell-quote. Those packages are patched in the validated Yarn graph.
CRA puts build tooling under dependencies, so npm's prod classification is not
browser runtime exposure. npm also counts vulnerable parent packages through
meta-advisories; Yarn counts advisory/path occurrences. These totals are not
comparable counts of unique vulnerabilities and neither is an exploitability proof.

| Scanner | Before | After |
| --- | --- | --- |
| Yarn advisory/path occurrences | 3 critical, 110 high, 50 moderate | 0 critical, 13 high, 16 moderate |
| Yarn unique advisory IDs | 2 critical, 34 high, 19 moderate | 0 critical, 3 high, 3 moderate |
| npm retained lockfile package entries | 2 critical, 73 high, 35 moderate, 6 low | unchanged; not the tested graph |
| pip-audit 2.10.1, pinned requirements | 29 records / 20 unique IDs / 8 packages | 23 records / 14 unique IDs / 5 packages |

The Python feed repeats some IDs; unique counts deduplicate by package/advisory.
The scan uses `--no-deps --disable-pip`: it covers listed pins, **not a complete
transitive/OS/container inventory**, and pins are not hash-locked. `pip check` passed
in the new isolated runtime. Audit databases are live; counts are a dated snapshot.

## Minimal fixes

- Browser libraries: Axios 1.18.0 → 1.20.0; react-router-dom 7.15.0 and resolved
  react-router 7.15.1 → 7.18.2. Existing SPA routes and API calls pass regressions.
- Targeted same-major build/dev patches: PostCSS 8.5.23, fast-uri 3.1.8,
  qs 6.16.0, follow-redirects 1.16.1, shell-quote 1.11.0, proxy-addr 2.0.8,
  compression 1.8.2, launch-editor 2.14.2, source-map-js 1.2.2,
  js-yaml 3.15.2/4.3.2 and postcss-svgo's SVGO 2.8.4. Brace-expansion
  re-resolves within its existing major ranges to 1.1.21/2.1.7. Yarn normalizes
  lock selectors and required transitive entries; React/CRA stay unchanged.
- Python: certifi 2026.10.19 (TLS trust bundle), PyJWT 2.15.0 and urllib3 2.8.0.
  No driver/framework major upgrade or dependency removal.
- Confirmed middleware issue: attacker-controlled Host URL reconstruction could
  disguise the routed path, bypass the origin check or omit auth cache protection.
  All three middleware/validation path checks now use ASGI `scope["path"]`, matching
  routing. Three malicious-Host tests fail against the original implementation and
  pass with the fix. Route auth and signed WhatsApp webhook handling remain intact.

## Critical/high Yarn advisory inventory

Each row identifies the baseline installed versions, all reported dependency paths,
first patched range, runtime exposure and disposition. Paths are scanner output;
`>` means a transitive dependency. Fixed means absent from the final Yarn audit,
not a claim that an attack was previously reachable. The browser uses Axios via
`src/lib/api.js`; routing is BrowserRouter, with no server-rendering/RSC handlers.
Build tooling processes repository assets/configuration, not customer uploads.
Never expose the development server or compile untrusted assets in a trusted build.

| Advisory / package / severity | Installed before | Dependency chains | Patched range | Exposure / disposition |
| --- | --- | --- | --- | --- |
| [1124252](https://github.com/advisories/GHSA-6g55-p6wh-862q) postcss (high) | 8.5.10 | `postcss`<br>`react-scripts>css-loader>postcss`<br>`react-scripts>postcss` | `>=8.5.12` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1139510](https://github.com/advisories/GHSA-r28c-9q8g-f849) postcss (high) | 8.5.10 | `postcss`<br>`react-scripts>css-loader>postcss`<br>`react-scripts>postcss` | `>=8.5.18` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1124276](https://github.com/advisories/GHSA-chx6-hx7r-mcp5) react-router (high) | 7.15.1 | `react-router-dom>react-router` | `>=7.18.0` | Browser SPA; no RSC or server routing. Route matching used client-side. Fixed in tested Yarn graph. |
| [1138769](https://github.com/advisories/GHSA-qwww-vcr4-c8h2) react-router (high) | 7.15.1 | `react-router-dom>react-router` | `>=7.18.2` | Browser SPA; no RSC or server routing. Route matching used client-side. Fixed in tested Yarn graph. |
| [1240104](https://github.com/advisories/GHSA-qhr7-859c-m2p7) brace-expansion (high) | 1.1.18 | `eslint>@eslint/config-array>minimatch>brace-expansion`<br>`eslint>minimatch>brace-expansion`<br>`react-scripts>babel-jest>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>babel-jest>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>eslint-config-react-app>eslint-plugin-jsx-a11y>minimatch>brace-expansion`<br>`react-scripts>jest>@jest/core>@jest/reporters>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>jest>@jest/core>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>jest>@jest/core>jest-config>babel-jest>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>@jest/test-sequencer>jest-runtime>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>@jest/test-sequencer>jest-runtime>jest-snapshot>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>babel-jest>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>react-dev-utils>fork-ts-checker-webpack-plugin>glob>minimatch>brace-expansion` | `>=1.1.20` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1240108](https://github.com/advisories/GHSA-6j4f-fj2g-mc7p) brace-expansion (high) | 1.1.18 | `eslint>@eslint/config-array>minimatch>brace-expansion`<br>`eslint>minimatch>brace-expansion`<br>`react-scripts>babel-jest>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>babel-jest>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>eslint-config-react-app>eslint-plugin-jsx-a11y>minimatch>brace-expansion`<br>`react-scripts>jest>@jest/core>@jest/reporters>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>jest>@jest/core>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>jest>@jest/core>jest-config>babel-jest>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>@jest/test-sequencer>jest-runtime>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>@jest/test-sequencer>jest-runtime>jest-snapshot>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>babel-jest>@jest/transform>babel-plugin-istanbul>test-exclude>glob>minimatch>brace-expansion`<br>`react-scripts>react-dev-utils>fork-ts-checker-webpack-plugin>glob>minimatch>brace-expansion` | `>=1.1.19` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1240603](https://github.com/advisories/GHSA-c29m-xwm3-cm6r) axios (high) | 1.18.0 | `axios` | `>=1.20.0` | Browser runtime; Node HTTP/proxy/HTTP2 advisories not used by this SPA; pollution gadgets require a separate pollution source. Fixed in tested Yarn graph. |
| [1240604](https://github.com/advisories/GHSA-mghh-pgcx-3jjj) axios (high) | 1.18.0 | `axios` | `>=1.20.0` | Browser runtime; Node HTTP/proxy/HTTP2 advisories not used by this SPA; pollution gadgets require a separate pollution source. Fixed in tested Yarn graph. |
| [1240605](https://github.com/advisories/GHSA-x97p-jq2g-jp4f) axios (high) | 1.18.0 | `axios` | `>=1.20.0` | Browser runtime; Node HTTP/proxy/HTTP2 advisories not used by this SPA; pollution gadgets require a separate pollution source. Fixed in tested Yarn graph. |
| [1240607](https://github.com/advisories/GHSA-3pq3-5fj3-cg6v) axios (high) | 1.18.0 | `axios` | `>=1.20.0` | Browser runtime; Node HTTP/proxy/HTTP2 advisories not used by this SPA; pollution gadgets require a separate pollution source. Fixed in tested Yarn graph. |
| [1240608](https://github.com/advisories/GHSA-542g-h47m-68v8) axios (high) | 1.18.0 | `axios` | `>=1.20.0` | Browser runtime; Node HTTP/proxy/HTTP2 advisories not used by this SPA; pollution gadgets require a separate pollution source. Fixed in tested Yarn graph. |
| [1240628](https://github.com/advisories/GHSA-m8m8-qj5v-23w3) axios (high) | 1.18.0 | `axios` | `>=1.20.0` | Browser runtime; Node HTTP/proxy/HTTP2 advisories not used by this SPA; pollution gadgets require a separate pollution source. Fixed in tested Yarn graph. |
| [1240634](https://github.com/advisories/GHSA-r4gj-5m52-g5wh) axios (high) | 1.18.0 | `axios` | `>=1.20.0` | Browser runtime; Node HTTP/proxy/HTTP2 advisories not used by this SPA; pollution gadgets require a separate pollution source. Fixed in tested Yarn graph. |
| [1124064](https://github.com/advisories/GHSA-v2hh-gcrm-f6hx) fast-uri (high) | 3.1.2 | `react-scripts>@pmmmwh/react-refresh-webpack-plugin>schema-utils>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv-formats>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv>fast-uri` | `>=3.1.4` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1130720](https://github.com/advisories/GHSA-7p8r-x3mc-p8w7) fast-uri (high) | 3.1.2 | `react-scripts>@pmmmwh/react-refresh-webpack-plugin>schema-utils>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv-formats>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv>fast-uri` | `>=3.1.5` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1158524](https://github.com/advisories/GHSA-f65p-4m7j-42xc) fast-uri (high) | 3.1.2 | `react-scripts>@pmmmwh/react-refresh-webpack-plugin>schema-utils>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv-formats>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv>fast-uri` | `>=3.1.6` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1158527](https://github.com/advisories/GHSA-fph4-wmhf-6fwf) fast-uri (high) | 3.1.2 | `react-scripts>@pmmmwh/react-refresh-webpack-plugin>schema-utils>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv-formats>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv>fast-uri` | `>=3.1.6` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1158530](https://github.com/advisories/GHSA-jqff-g426-hqxp) fast-uri (high) | 3.1.2 | `react-scripts>@pmmmwh/react-refresh-webpack-plugin>schema-utils>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv-formats>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv>fast-uri` | `>=3.1.6` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1204921](https://github.com/advisories/GHSA-4c8g-83qw-93j6) fast-uri (high) | 3.1.2 | `react-scripts>@pmmmwh/react-refresh-webpack-plugin>schema-utils>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv-formats>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv>fast-uri` | `>=3.1.3` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1239943](https://github.com/advisories/GHSA-qw65-cvwx-89v3) fast-uri (high) | 3.1.2 | `react-scripts>@pmmmwh/react-refresh-webpack-plugin>schema-utils>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv-formats>ajv>fast-uri`<br>`react-scripts>webpack>minimizer-webpack-plugin>schema-utils>ajv>fast-uri` | `>=3.1.7` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1138115](https://github.com/advisories/GHSA-5p4m-2wfm-xmqj) js-yaml (high) | 4.3.0 | `eslint>@eslint/eslintrc>js-yaml`<br>`react-scripts>eslint>@eslint/eslintrc>js-yaml` | `>=4.3.1` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1193727](https://github.com/advisories/GHSA-2883-xcg3-v3hh) js-yaml (high) | 4.3.0 | `eslint>@eslint/eslintrc>js-yaml`<br>`react-scripts>eslint>@eslint/eslintrc>js-yaml` | `>=4.3.2` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1139520](https://github.com/advisories/GHSA-2p49-hgcm-8545) svgo (high) | 1.3.2, 2.8.1 | `react-scripts>@svgr/webpack>@svgr/plugin-svgo>svgo`<br>`react-scripts>css-minimizer-webpack-plugin>cssnano>cssnano-preset-default>postcss-svgo>svgo` | `>=2.8.3` | Build SVG optimization, not upload sanitization. 2.x patched; remaining 1.3.2 requires incompatible SVGR/CRA migration; deferred. |
| [1193737](https://github.com/advisories/GHSA-w27v-7q3p-w38r) svgo (high) | 1.3.2, 2.8.1 | `react-scripts>@svgr/webpack>@svgr/plugin-svgo>svgo`<br>`react-scripts>css-minimizer-webpack-plugin>cssnano>cssnano-preset-default>postcss-svgo>svgo` | `>=2.8.4` | Build SVG optimization, not upload sanitization. 2.x patched; remaining 1.3.2 requires incompatible SVGR/CRA migration; deferred. |
| [1240105](https://github.com/advisories/GHSA-qhr7-859c-m2p7) brace-expansion (high) | 2.1.4 | `react-scripts>workbox-webpack-plugin>workbox-build>@surma/rollup-plugin-off-main-thread>ejs>jake>filelist>minimatch>brace-expansion` | `>=2.1.6` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1240109](https://github.com/advisories/GHSA-6j4f-fj2g-mc7p) brace-expansion (high) | 2.1.4 | `react-scripts>workbox-webpack-plugin>workbox-build>@surma/rollup-plugin-off-main-thread>ejs>jake>filelist>minimatch>brace-expansion` | `>=2.1.5` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1241209](https://github.com/advisories/GHSA-68fv-2mgg-jv7q) source-map-js (high) | 1.2.1 | `postcss>source-map-js`<br>`react-scripts>css-loader>postcss>source-map-js`<br>`react-scripts>postcss>source-map-js` | `>=1.2.2` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1241210](https://github.com/advisories/GHSA-jqcg-44mw-7w3h) proxy-addr (critical) | 2.0.7 | `react-scripts>webpack-dev-server>express>proxy-addr` | `>=2.0.8` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1241221](https://github.com/advisories/GHSA-vc2v-76pw-4v95) compression (high) | 1.8.1 | `react-scripts>webpack-dev-server>compression` | `>=1.8.2` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1241332](https://github.com/advisories/GHSA-pqg4-j6r4-53mv) shell-quote (critical) | 1.9.0 | `react-scripts>react-dev-utils>shell-quote`<br>`react-scripts>webpack-dev-server>launch-editor>shell-quote` | `>=1.11.0` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1242604](https://github.com/advisories/GHSA-q3jh-wrc6-jgq8) follow-redirects (high) | 1.16.0 | `axios>follow-redirects`<br>`http-proxy-middleware>http-proxy>follow-redirects`<br>`react-scripts>webpack-dev-server>http-proxy-middleware>http-proxy>follow-redirects` | `>=1.16.1` | Node Axios/dev proxy only; browser uses its native transport. Fixed in tested Yarn graph. |
| [1242605](https://github.com/advisories/GHSA-8r9p-f939-6h3c) follow-redirects (high) | 1.16.0 | `axios>follow-redirects`<br>`http-proxy-middleware>http-proxy>follow-redirects`<br>`react-scripts>webpack-dev-server>http-proxy-middleware>http-proxy>follow-redirects` | `>=1.16.1` | Node Axios/dev proxy only; browser uses its native transport. Fixed in tested Yarn graph. |
| [1242663](https://github.com/advisories/GHSA-587h-7wmj-h5pm) launch-editor (high) | 2.14.1 | `react-scripts>webpack-dev-server>launch-editor` | `>=2.14.2` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1138114](https://github.com/advisories/GHSA-5p4m-2wfm-xmqj) js-yaml (high) | 3.15.0 | `react-scripts>@svgr/webpack>@svgr/plugin-svgo>svgo>js-yaml`<br>`react-scripts>babel-jest>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>babel-jest>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>jest>@jest/core>@jest/reporters>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>jest>@jest/core>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>jest>@jest/core>jest-config>babel-jest>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>@jest/test-sequencer>jest-runtime>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>@jest/test-sequencer>jest-runtime>jest-snapshot>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>babel-jest>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml` | `>=3.15.1` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1193726](https://github.com/advisories/GHSA-2883-xcg3-v3hh) js-yaml (high) | 3.15.0 | `react-scripts>@svgr/webpack>@svgr/plugin-svgo>svgo>js-yaml`<br>`react-scripts>babel-jest>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>babel-jest>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>jest>@jest/core>@jest/reporters>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>jest>@jest/core>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>jest>@jest/core>jest-config>babel-jest>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>@jest/test-sequencer>jest-runtime>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>@jest/test-sequencer>jest-runtime>jest-snapshot>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>babel-jest>@jest/transform>babel-plugin-istanbul>@istanbuljs/load-nyc-config>js-yaml` | `>=3.15.2` | Build/dev only; no browser execution. Fixed in tested Yarn graph. |
| [1240992](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) braces (high) | 3.0.3 | `http-proxy-middleware>micromatch>braces`<br>`react-scripts>eslint-config-react-app>@typescript-eslint/eslint-plugin>@typescript-eslint/type-utils>@typescript-eslint/typescript-estree>globby>fast-glob>micromatch>braces`<br>`react-scripts>eslint-config-react-app>@typescript-eslint/eslint-plugin>@typescript-eslint/type-utils>@typescript-eslint/utils>@typescript-eslint/typescript-estree>globby>fast-glob>micromatch>braces`<br>`react-scripts>eslint-config-react-app>@typescript-eslint/parser>@typescript-eslint/typescript-estree>globby>fast-glob>micromatch>braces`<br>`react-scripts>jest>@jest/core>@jest/transform>jest-haste-map>micromatch>braces`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>@jest/test-sequencer>jest-runtime>@jest/globals>@jest/environment>@jest/fake-timers>jest-message-util>micromatch>braces`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>@jest/test-sequencer>jest-runtime>@jest/transform>jest-haste-map>micromatch>braces`<br>`react-scripts>jest>jest-cli>@jest/core>jest-config>@jest/test-sequencer>jest-runtime>jest-snapshot>@jest/transform>jest-haste-map>micromatch>braces`<br>`react-scripts>react-dev-utils>globby>fast-glob>micromatch>braces`<br>`react-scripts>webpack-dev-server>http-proxy-middleware>micromatch>braces`<br>`tailwindcss>fast-glob>micromatch>braces` | `<0.0.0` | Build/dev glob parsing; no patched release. Untrusted patterns must not enter tooling; deferred. |

## Remaining frontend findings

All six remaining unique advisories are tooling-only in this application:
SVGO 1.3.2 (two high, one moderate; first compatible-major fix unavailable),
braces 3.0.3 (one high; no patch), postcss-selector-parser 6.1.4/7.1.5 (one
moderate; patched 7.1.6 would force the 6.x consumers across a major), and sprintf-js
1.0.3 (one moderate; no patch). No browser runtime high/critical finding remains
in this audit. Do not interpret this as a general security guarantee.

SVGO's [sanitization advisory](https://github.com/advisories/GHSA-2p49-hgcm-8545)
requires reliance on its removeScripts plugin for sanitization; this application
uses it in the repository build, not a customer SVG sanitization service.
The [braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) has no
patched version. Replacing CRA/SVGR or a glob library is outside this safe patch.

## Python findings and disposition

Authentication uses PyJWT with a fixed HS256 allowlist; no python-jose, ECDSA
signing, OAuth authorization server, JWKS, GridFS or client-side encryption path
was found in application code. Mongo URI comes from server configuration, not
request interpolation. These observations reduce exposure, not package findings.

| Package | Remaining advisory IDs | Patched version(s) | Disposition |
| --- | --- | --- | --- |
| ecdsa 0.19.2 | PYSEC-2026-1325 | PYSEC-2026-1325: none | No application signing path; no patch. Retain pending dependency impact review. |
| oauthlib 3.3.1 | PYSEC-2026-4114 | PYSEC-2026-4114: 4.0.0 | Authorization-server PKCE path not used. 4.x upgrade deferred. |
| pymongo 4.6.3 | PYSEC-2026-4295<br>PYSEC-2026-4294<br>PYSEC-2026-4297<br>PYSEC-2026-4296 | PYSEC-2026-4295: 4.18.2<br>PYSEC-2026-4294: 4.18.1<br>PYSEC-2026-4297: 4.18.2<br>PYSEC-2026-4296: 4.18.2 | CSFLE/KMS, GridFS, URI and huge BSON cases. Relevant database driver remains; no proven request exploit in this pass. Motor 3.3.1 compatibility must be validated before upgrading driver internals; hold deployment pending review. No unsafe isolated driver bump. |
| python-jose 3.5.0 | PYSEC-2026-4298 | PYSEC-2026-4298: none | Not the application JWT decoder; no patch. Retain pending dependency impact review. |
| starlette 0.37.2 | PYSEC-2026-1943<br>PYSEC-2026-1941<br>PYSEC-2026-161<br>PYSEC-2026-2281<br>PYSEC-2026-2280<br>PYSEC-2026-249<br>PYSEC-2026-248 | PYSEC-2026-1943: 0.40.0<br>PYSEC-2026-1941: 0.47.2<br>PYSEC-2026-161: 1.0.1<br>PYSEC-2026-2281: 1.1.0<br>PYSEC-2026-2280: 1.1.0<br>PYSEC-2026-249: 1.3.1<br>PYSEC-2026-248: 1.3.0 | Host/path origin/cache exposure mitigated in application with regression tests. No multipart/Form/StaticFiles/HTTPEndpoint application handlers found. Remaining framework advisories retained; patched versions exceed FastAPI 0.110.1 constraints (<0.38), requiring coordinated migration. Do not override constraints. |

## Reproduction and results

From an isolated frontend copy with no node_modules (do not reuse the developer's
symlinked install):

```sh
npx --yes yarn@1.22.22 install --frozen-lockfile --ignore-scripts --non-interactive
npx --yes yarn@1.22.22 audit --json
npm audit --json
CI=true npx --yes yarn@1.22.22 test --watchAll=false --runInBand
CI=true npx --yes yarn@1.22.22 build
```

Audit exits are nonzero because findings remain; Yarn's status is a severity
bitmask, not a network failure. Frontend **134 passed / 12 suites**, production
build **compiled successfully**. Existing peer/resolution warnings remain.

```sh
python3 -m venv /tmp/rushx-pip-audit-venv
/tmp/rushx-pip-audit-venv/bin/pip install pip-audit==2.10.1
/tmp/rushx-pip-audit-venv/bin/pip-audit --no-deps --disable-pip -r backend/requirements.txt -f json
python3 -m venv /tmp/rushx-backend-security-venv
/tmp/rushx-backend-security-venv/bin/pip install -r backend/requirements.txt -r backend/requirements-test.txt
/tmp/rushx-backend-security-venv/bin/pip check
# From backend, with a local test API and disposable Mongo database as below:
/tmp/rushx-backend-security-venv/bin/python -m pytest tests -q -rs
```

Full backend: **246 passed, 2 skipped, 11 warnings**. Skips: empty owner wallet and
no withdrawals; existing multipart/lifespan/mongomock warnings. The local harness
`/tmp/voltx_issue3_regression.py` ran uvicorn on 127.0.0.1:18093 and pytest using
APP_ENV=test, OTP_MODE=demo, EXPOSE_DEMO_OTP=true, WHATSAPP_ENABLED=false,
CORS_ORIGINS=http://localhost:3000 and REACT_APP_BACKEND_URL=http://127.0.0.1:18093.
It generated a fresh `voltx_wa_test_*` DB from the local configured Mongo connection
and removed only that DB afterward. It is a local harness, not a repository script;
other environments must provision an equivalent isolated test API/database. All
Meta calls remain mocked. No real payments or production data changes.

Additional static check: `python -m pyflakes backend/server.py
backend/tests/test_safety_gate.py` reports three pre-existing server warnings
(unused math, timedelta and admin_id), reproduced against the baseline; no new
warnings in the changed tests. An extra targeted pytest invocation from the repo
root failed collection because tests expect the backend working directory; rerun
from backend passed. These do not invalidate the complete backend run above.

## Merge vs deployment recommendation

**Merge: HOLD for reviewer disposition of the residual dependency risks and the
previous safety gate's outstanding decisions.** The compatible fixes pass tests;
this pass does not require a risky framework/toolchain rewrite to appear clean.
Reviewers may explicitly accept bounded build-only risks, but this task does not
supply that acceptance. No merge was performed.

**Deployment: NOT READY.** Confirm and enforce the actual frozen Yarn installer,
review/resolve the retained npm graph if it is used, assess the remaining Python
framework/driver findings, and complete prior operational/merchant/Meta/backup/load
checks. No live validation, OS/container audit or production installer verification
was possible from this repository. No Meta settings, credentials, message gates,
payment flows, repair transitions or production data were changed.
