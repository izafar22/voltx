const { defineConfig } = require("@playwright/test");
module.exports = defineConfig({
  testDir: ".",
  testMatch: "public.spec.cjs",
  workers: 2,
  use: { baseURL: "http://127.0.0.1:3100", browserName: "chromium" },
  projects: [320, 375, 768, 1280].map((width) => ({
    name: String(width),
    use: { viewport: { width, height: 900 } },
  })),
  webServer: {
    command: "node server.cjs",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: false,
  },
});
