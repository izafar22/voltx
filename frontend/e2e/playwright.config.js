const { defineConfig } = require("@playwright/test");
module.exports = defineConfig({
  testDir: ".",
  testMatch: "auth.spec.js",
  timeout: 30000,
  fullyParallel: true,
  workers: 2,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:3100",
    browserName: "chromium",
    serviceWorkers: "block",
    trace: "off",
  },
  projects: [320, 375, 768, 1280].map((width) => ({
    name: `width-${width}`,
    use: { viewport: { width, height: width < 768 ? 850 : 900 } },
  })),
  webServer: {
    command: "node server.cjs",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: false,
  },
});
