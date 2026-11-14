const { defineConfig } = require("@playwright/test");
module.exports = defineConfig({
  testDir: ".",
  testMatch: "storybook.spec.cjs",
  outputDir: "test-results-storybook",
  workers: 2,
  timeout: 30000,
  expect: {
    toHaveScreenshot: { animations: "disabled", maxDiffPixelRatio: 0.002 },
  },
  snapshotPathTemplate:
    "{testDir}/storybook-snapshots/{platform}/{projectName}/{arg}{ext}",
  use: {
    baseURL: "http://127.0.0.1:6106",
    browserName: "chromium",
    colorScheme: "light",
    reducedMotion: "reduce",
  },
  projects: [375, 1280].map((width) => ({
    name: String(width),
    grepInvert: width === 375 ? /manager toolbar/ : undefined,
    use: { viewport: { width, height: 900 } },
  })),
  webServer: {
    command: "node storybook-server.cjs",
    url: "http://127.0.0.1:6106",
    reuseExistingServer: false,
  },
});
