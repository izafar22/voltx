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
      page.getByRole("link", { name: "Book a Repair", exact: true }).first(),
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
    if (pathname === "/") {
      const hero = page.locator('[data-story-asset="hero"]');
      const image = hero.locator("img");
      await expect(image).toHaveAttribute("src", /rushx-workshop-1280\.webp$/);
      await expect(hero.locator("figcaption")).toHaveCount(0);
      await expect(image).toBeVisible();
      await expect.poll(() => image.evaluate((img) => img.complete && img.naturalWidth > 0)).toBe(true);
      expect(await image.evaluate((img) => img.currentSrc)).toContain("/rushx-workshop-");
      const geometry = await image.evaluate((img) => ({
        width: img.getBoundingClientRect().width,
        height: img.getBoundingClientRect().height,
        fit: getComputedStyle(img).objectFit,
      }));
      expect(geometry.width / geometry.height).toBeCloseTo(1.5, 1);
      expect(geometry.fit).toBe("cover");
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
    .getByRole("link", { name: "Book a Repair", exact: true })
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
  expect(
    (
      await new AxeBuilder({ page })
        .include(".rx-public")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(page.locator("html")).toHaveCSS("color-scheme", "dark");
  expect(
    (
      await new AxeBuilder({ page })
        .include(".rx-public")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  const publicSurface = await page
    .locator(".rx-public")
    .evaluate((el) => getComputedStyle(el).backgroundColor);
  await page
    .getByRole("link", { name: "Book a Repair", exact: true })
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
for (const theme of ["light", "dark"])
  test(`unified home, login and dashboard / ${theme}`, async ({
    page,
  }, info) => {
    await page.addInitScript(
      (t) => localStorage.setItem("rushx-theme", t),
      theme,
    );
    const audit = async () => {
      await page.evaluate(
        () =>
          new Promise((r) =>
            requestAnimationFrame(() => requestAnimationFrame(r)),
          ),
      );
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      const results = await new AxeBuilder({ page })
        .include(".App")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      expect(
        results.violations.map((v) => ({
          id: v.id,
          nodes: v.nodes.map((n) => n.target),
        })),
      ).toEqual([]);
    };
    const screenshot = async (name) => {
      const dir = path.join(
        __dirname,
        "test-results",
        "unified",
        info.project.name,
      );
      fs.mkdirSync(dir, { recursive: true });
      await page.screenshot({
        path: path.join(dir, `${name}-${theme}.png`),
        fullPage: true,
      });
    };
    await page.goto("/");
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.locator("html")).toHaveCSS("color-scheme", theme);
    await audit();
    await screenshot("home");
    await page.goto("/login");
    await expect(page.getByLabel("Phone number")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Continue with Google" }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Explore RushX", exact: true }),
    ).toHaveAttribute("href", "/");
    await expect(page.locator("html")).toHaveCSS("color-scheme", theme);
    await audit();
    await screenshot("login");
    await page.route("**/api/auth/me", (r) =>
      r.fulfill({
        json: {
          role: "customer",
          user_id: "demo",
          name: "Illustrative Customer",
        },
      }),
    );
    await page.goto("/app");
    await expect(
      page.getByText("No repair requests yet", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: "Repair when possible. Replace when necessary.",
      }),
    ).toBeVisible();
    await expect(page.locator("html")).toHaveCSS("color-scheme", theme);
    await audit();
    await screenshot("dashboard");
    if (Number(info.project.name) < 1024)
      await page
        .getByRole("button", { name: "Open navigation", exact: true })
        .click();
    await page
      .getByRole("link", { name: "Explore RushX", exact: true })
      .click();
    await expect(page).toHaveURL(/\/$/);
    await page.reload();
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.locator("html")).toHaveCSS("color-scheme", theme);
  });
test("persisted dark theme is applied before React loads", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("rushx-theme", "dark"));
  await page.route("**/static/js/**", (r) => r.abort());
  await page.goto("/login");
  await expect(page.locator("html")).toHaveClass(/dark/);
  await expect(page.locator("html")).toHaveCSS("color-scheme", "dark");
  expect(await page.locator("#root").textContent()).toBe("");
});
test("Google entry remains same-origin and resumes the pending repair after callback", async ({
  page,
}) => {
  let requested = false;
  await page.route("**/api/auth/google/login", (r) => {
    requested = true;
    return r.fulfill({ status: 302, headers: { location: "/login" } });
  });
  await page.goto("/repairs/new");
  await expect(page).toHaveURL(/\/login$/);
  await page
    .getByRole("button", { name: "Continue with Google", exact: true })
    .click();
  await expect.poll(() => requested).toBe(true);
  await expect(page).toHaveURL(/\/login$/);
  await page.route("**/api/auth/me", (r) =>
    r.fulfill({
      json: {
        user_id: "demo",
        name: "Illustrative Customer",
        role: "customer",
      },
    }),
  );
  await page.goto("/login");
  await expect(page).toHaveURL(/\/repairs\/new$/);
  await expect(page.locator("h1")).toContainText(/repair/i);
});
for (const [route, count] of [
  ["/", 2],
  ["/services", 4],
  ["/how-it-works", 5],
  ["/about", 1],
])
  for (const theme of ["light", "dark"])
    test(`visual storytelling ${route} / ${theme}`, async ({ page }) => {
      await page.addInitScript((t) => {
        localStorage.setItem("rushx-theme", t);
        window.__artCLS = 0;
        new PerformanceObserver((list) => {
          for (const e of list.getEntries())
            if (!e.hadRecentInput) window.__artCLS += e.value;
        }).observe({ type: "layout-shift", buffered: true });
      }, theme);
      await page.goto(route);
      await expect(page.locator("h1")).toBeVisible();
      const titleBefore = await page.locator("h1").boundingBox();
      const images = page.locator(".rx-story-image img");
      await expect(images).toHaveCount(count);
      for (const img of await images.all()) {
        expect((await img.getAttribute("alt")).length).toBeGreaterThan(30);
        expect(await img.getAttribute("srcset")).toMatch(/\d+w/);
        expect(await img.getAttribute("sizes")).toBeTruthy();
        expect(Number(await img.getAttribute("width"))).toBeGreaterThan(0);
        expect(Number(await img.getAttribute("height"))).toBeGreaterThan(0);
        await img.scrollIntoViewIfNeeded();
        await img.evaluate((i) => i.decode());
        expect(
          await img.evaluate(
            (i) =>
              i.naturalWidth > 0 &&
              i.naturalHeight > 0 &&
              new URL(i.currentSrc).origin === location.origin,
          ),
        ).toBe(true);
        expect(await img.getAttribute("loading")).toBe(
          (await img.getAttribute("fetchpriority")) === "high"
            ? "eager"
            : "lazy",
        );
        expect(await img.getAttribute("src")).toContain(
          "/assets/visual-storytelling/",
        );
      }
      await expect(page.locator(".rx-process-art")).toHaveCount(0);
      await expect(page.locator(".rx-story-coverage")).toHaveCount(1);
      await expect(page.locator(".rx-final")).toHaveCount(0);
      const assetIds = await page
        .locator("[data-story-asset]")
        .evaluateAll((nodes) => nodes.map((n) => n.dataset.storyAsset));
      expect(new Set(assetIds).size).toBe(count);
      await expect(
        page.locator('.rx-story-image img[fetchpriority="high"]'),
      ).toHaveCount(route === "/" || route === "/about" ? 1 : 0);
      await page.evaluate(() => scrollTo(0, 0));
      await page.evaluate(
        () =>
          new Promise((r) =>
            requestAnimationFrame(() => requestAnimationFrame(r)),
          ),
      );
      const titleAfter = await page.locator("h1").boundingBox();
      expect(Math.abs(titleAfter.y - titleBefore.y)).toBeLessThan(1);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      expect(await page.evaluate(() => window.__artCLS)).toBeLessThanOrEqual(
        0.02,
      );
      const a11y = await new AxeBuilder({ page })
        .include(".rx-public")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      expect(
        a11y.violations.map((v) => ({
          id: v.id,
          nodes: v.nodes.map((n) => n.target),
        })),
      ).toEqual([]);
    });

for (const theme of ["light", "dark"])
  test(`WhatsApp button exact brand colour and geometry / ${theme}`, async ({ page }) => {
    await page.addInitScript(
      (t) => localStorage.setItem("rushx-theme", t),
      theme,
    );
    await page.goto("/");
    await expect(page.locator("html")).toHaveCSS("color-scheme", theme);
    const button = page.getByTestId("whatsapp-chat-link");
    await expect(button).toBeVisible();
    await expect(button).toHaveCSS("background-color", "rgb(37, 211, 102)");
    await expect(button).toHaveCSS("width", "56px");
    await expect(button).toHaveCSS("height", "56px");
    await expect(button).toHaveCSS("position", "fixed");
    await expect(button).toHaveCSS("bottom", "24px");
    await expect(button).toHaveCSS("right", "24px");
    await expect(button).toHaveCSS("border-radius", "9999px");
    await expect(button).toHaveCSS("box-shadow", /rgba\(0, 0, 0, 0\.18\) 0px 5px 18px 0px/);
    const icon = button.locator("svg");
    await expect(icon).toHaveCSS("width", "32px");
    await expect(icon).toHaveCSS("height", "32px");
    await expect(icon).toHaveCSS("fill", "rgb(255, 255, 255)");
    await button.hover();
    await expect(button).toHaveCSS("transform", "matrix(1.05, 0, 0, 1.05, 0, 0)");
    await expect(button).toHaveCSS("background-color", "rgb(37, 211, 102)");
  });
