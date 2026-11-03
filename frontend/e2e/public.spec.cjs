const { test, expect } = require("@playwright/test");
const fs = require("fs");
const AxeBuilder = require("@axe-core/playwright").default;
const path = require("path");
const pages = ["/", "/services", "/about", "/how-it-works", "/faq"];
test.beforeEach(async ({ page }) => {
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== "http://127.0.0.1:3100") return route.abort();
    if (url.pathname === "/api/repairs") return route.fulfill({ json: [] });
    if (url.pathname === "/api/auth/me")
      return route.fulfill({ status: 401, json: { detail: "Sign in" } });
    return route.continue();
  });
});
for (const pathname of pages)
  test(`${pathname} public content, navigation, metadata and layout`, async ({
    page,
  }, info) => {
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(pathname);
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.locator("link[rel=canonical]")).toHaveAttribute(
      "href",
      "https://evchargerrepair.in" + pathname,
    );
    await expect(page.locator('meta[property="og:url"]')).toHaveAttribute(
      "content",
      "https://evchargerrepair.in" + pathname,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await expect(
      page.getByRole("link", { name: "Request a repair", exact: true }).first(),
    ).toHaveAttribute("href", "/repairs/new");
    if (Number(info.project.name) < 901) {
      await page.getByRole("button", { name: "Open menu" }).click();
      await expect(
        page.getByRole("navigation", { name: "Main navigation" }),
      ).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(
        page.getByRole("button", { name: "Open menu" }),
      ).toBeFocused();
    }
    if (pathname === "/faq") {
      const question = page.locator("summary").first();
      await question.focus();
      await page.keyboard.press("Enter");
      await expect(page.locator("details").first()).toHaveAttribute("open", "");
    }
    const dir = path.join(
      __dirname,
      "test-results",
      "screenshots",
      info.project.name,
    );
    fs.mkdirSync(dir, { recursive: true });
    await page.screenshot({
      path: path.join(
        dir,
        (pathname === "/" ? "home" : pathname.slice(1)) + ".png",
      ),
      fullPage: true,
    });
    expect(errors).toEqual([]);
  });
test("service cards link to matching details and primary CTA retains destination", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: /PCB & control boards/ }).click();
  await expect(page).toHaveURL(/\/services#pcb$/);
  await expect(page.locator("#pcb")).toBeInViewport();
  await page
    .getByRole("link", { name: "Request an assessment" })
    .first()
    .click();
  await expect(page).toHaveURL(/\/login$/);
  expect(
    await page.evaluate(() =>
      sessionStorage.getItem("rushx.repair-destination"),
    ),
  ).toBe("/repairs/new");
  await expect(
    page.getByRole("button", { name: "Continue with Google" }),
  ).toBeVisible();
  await expect(page.getByLabel("Phone number")).toBeVisible();
});
test("SMS sign-in resumes existing repair form", async ({ page }) => {
  await page.route("**/api/auth/request-otp", (r) =>
    r.fulfill({ json: { challenge_id: "test", resend_after: 60 } }),
  );
  await page.route("**/api/auth/verify-otp", (r) =>
    r.fulfill({
      json: {
        user: {
          user_id: "test",
          name: "Test Customer",
          role: "customer",
          phone: "+919876543210",
        },
      },
    }),
  );
  await page.goto("/");
  await page
    .getByRole("link", { name: "Request a repair", exact: true })
    .first()
    .click();
  await page.getByLabel("Phone number").fill("9876543210");
  await page.getByRole("button", { name: "Send OTP", exact: true }).click();
  await page.getByLabel("Six-digit code").fill("123456");
  await page.getByRole("button", { name: "Verify", exact: true }).click();
  await expect(page).toHaveURL(/\/repairs\/new$/);
  await expect(page.locator("h1")).toContainText(/repair/i);
});
test("Google callback session resumes intended repair and public home stays accessible", async ({
  page,
}) => {
  await page.goto("/repairs/new");
  await expect(page).toHaveURL(/\/login$/);
  await page.unroute("**/*");
  await page.route("**/*", (r) => {
    const u = new URL(r.request().url());
    if (u.origin !== "http://127.0.0.1:3100") return r.abort();
    if (u.pathname === "/api/auth/me")
      return r.fulfill({
        json: { user_id: "test", role: "customer", name: "Test Customer" },
      });
    return r.continue();
  });
  await page.goto("/login");
  await expect(page).toHaveURL(/\/repairs\/new$/);
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("Repair when possible.");
  if (
    test.info().project.name === "320" ||
    test.info().project.name === "375" ||
    test.info().project.name === "768"
  )
    await page.getByRole("button", { name: "Open menu" }).click();
  await expect(
    page.getByRole("link", { name: "My account", exact: true }),
  ).toHaveAttribute("href", "/app");
});

test("public theme persists through existing login and an authenticated screen", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".rx-public")).toBeVisible();
  expect((await new AxeBuilder({page}).include(".rx-public").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze()).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))).toEqual([]);
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(page.locator("html")).toHaveCSS("color-scheme", "dark");
  expect((await new AxeBuilder({page}).include(".rx-public").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze()).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))).toEqual([]);
  const publicSurface = await page
    .locator(".rx-public")
    .evaluate((el) => getComputedStyle(el).backgroundColor);
  await page
    .getByRole("link", { name: "Request a repair", exact: true })
    .first()
    .click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.locator("html")).toHaveCSS("color-scheme", "dark");
  await page.route("**/api/auth/me", (r) =>
    r.fulfill({
      json: {
        user_id: "demo",
        role: "customer",
        name: "Illustrative Customer",
      },
    }),
  );
  await page.goto("/app");
  await expect(page.locator(".customer-shell")).toBeVisible();
  expect(
    await page
      .locator(".customer-shell")
      .evaluate((el) => getComputedStyle(el).backgroundColor),
  ).toBe(publicSurface);
  await page.getByRole("button", { name: "Switch to light theme" }).click();
  await expect(page.locator("html")).toHaveCSS("color-scheme", "light");
});
