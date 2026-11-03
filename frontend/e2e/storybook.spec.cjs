const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;
const fs = require("fs");
const path = require("path");
const entries = Object.values(
  JSON.parse(
    fs.readFileSync(
      path.join(__dirname, "../storybook-static/index.json"),
      "utf8",
    ),
  ).entries,
).filter((e) => e.type === "story");
test.beforeEach(async ({ page }) => {
  await page.route("**/*", (r) =>
    new URL(r.request().url()).origin === "http://127.0.0.1:6106"
      ? r.continue()
      : r.abort(),
  );
});
async function open(page, id, theme) {
  await page.goto(
    `/iframe.html?id=${id}&viewMode=story&globals=theme:${theme}`,
  );
  await expect(page.locator(".ds-canvas")).toBeVisible();
  await expect(page.locator("html")).toHaveCSS("color-scheme", theme);
  await page.evaluate(() => document.fonts.ready);
  // Theme effects must be painted before axe snapshots inherited text colors.
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)),
      ),
  );
}
for (const entry of entries)
  for (const theme of ["light", "dark"])
    test(`${entry.id} / ${theme} renders accessibly`, async ({ page }) => {
      const errors = [];
      page.on("pageerror", (e) => errors.push(e.message));
      await open(page, entry.id, theme);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      const results = await new AxeBuilder({ page })
        .include(".ds-canvas")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      expect(
        results.violations.map((v) => ({
          id: v.id,
          nodes: v.nodes.map((n) => n.target),
        })),
      ).toEqual([]);
      expect(errors).toEqual([]);
    });
for (const theme of ["light", "dark"])
  test(`visual baseline / ${theme}`, async ({ page }) => {
    await open(page, "patterns-repair--services", theme);
    await expect(page.locator(".ds-canvas")).toHaveScreenshot(
      `services-${theme}.png`,
    );
  });
test("shared theme toggle persists and network guard prevents live auth", async ({
  page,
}) => {
  await open(page, "components-shared--theme-switch", "light");
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(page.locator("html")).toHaveCSS("color-scheme", "dark");
  expect(await page.evaluate(() => localStorage.getItem("rushx-theme"))).toBe(
    "dark",
  );
  const message = await page.evaluate(() =>
    fetch("/api/auth/me")
      .then(() => "unexpected success")
      .catch((e) => e.message),
  );
  expect(message).toContain("Live network is disabled");
});
test("manager toolbar controls shared theme and mobile viewport", async ({
  page,
}) => {
  await page.goto(
    "/?path=/story/components-shared--navigation&globals=theme:light",
  );
  const frame = page.frameLocator("#storybook-preview-iframe");
  await expect(frame.locator(".ds-canvas")).toBeVisible();
  await page
    .getByRole("button", {
      name: "RushX theme (shared ThemeContext) light",
      exact: true,
    })
    .click();
  await page.getByText("dark", { exact: true }).last().click();
  await expect(frame.locator("html")).toHaveCSS("color-scheme", "dark");
  await page
    .getByRole("button", { name: "Viewport size", exact: true })
    .click();
  await page.getByText("Mobile 375", { exact: true }).click();
  await expect
    .poll(() => frame.locator("html").evaluate(() => innerWidth))
    .toBe(375);
});
