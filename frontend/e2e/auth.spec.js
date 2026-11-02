const { test, expect } = require("@playwright/test");
const customer = {
  user_id: "synthetic-customer",
  name: "Test Customer",
  role: "customer",
  phone: "+919876543210",
  phone_verified: true,
};
async function mockApi(
  page,
  { initial = null, newCustomer = false, unavailable = false } = {},
) {
  let user = initial,
    verifications = 0,
    lastRepair = null;
  await page
    .context()
    .route("**/*", (route) =>
      new URL(route.request().url()).origin === "http://127.0.0.1:3100"
        ? route.continue()
        : route.abort(),
    );
  await page.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const body =
      route.request().method() === "POST"
        ? route.request().postDataJSON()
        : null;
    if (pathname === "/api/auth/me")
      return route.fulfill({
        status: user ? 200 : 401,
        json: user || { detail: "Not authenticated" },
      });
    if (pathname.endsWith("/request-otp"))
      return route.fulfill({
        status: unavailable ? 503 : 200,
        json: unavailable
          ? { detail: "Unavailable" }
          : {
              challenge_id: "browser-challenge",
              expires_in: 300,
              resend_after: 60,
            },
      });
    if (pathname === "/api/auth/phone/verify-otp") {
      verifications++;
      user = { ...user, phone: body.phone, phone_verified: true };
      return route.fulfill({ json: { user } });
    }
    if (pathname === "/api/auth/verify-otp") {
      verifications++;
      if (body.otp !== "654321")
        return route.fulfill({
          status: 400,
          json: { detail: "Incorrect code" },
        });
      if (newCustomer)
        return route.fulfill({
          json: {
            registration_required: true,
            registration_token: "synthetic-grant",
          },
        });
      user = { ...customer };
      return route.fulfill({ json: { user } });
    }
    if (pathname === "/api/auth/register-customer") {
      user = { ...customer, name: body.name };
      return route.fulfill({ json: { user } });
    }
    if (pathname === "/api/auth/logout") {
      user = null;
      return route.fulfill({ json: { ok: true } });
    }
    if (pathname === "/api/repairs" && body) {
      lastRepair = body;
      return route.fulfill({
        json: {
          id: "synthetic-repair",
          repair_request_number: "REP-TEST",
          status: "REQUESTED",
        },
      });
    }
    return route.fulfill({ json: [] });
  });
  return { verificationCount: () => verifications, repair: () => lastRepair };
}
async function noOverflow(page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
}
async function enterPhone(page) {
  await page.getByLabel("Mobile number", { exact: true }).fill("9876543210");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByLabel("Six-digit code")).toBeVisible();
}

test("existing customer auto-verifies and reaches dashboard", async ({
  page,
}, info) => {
  const api = await mockApi(page);
  await page.goto("/login");
  await expect(page.getByLabel("Mobile number", { exact: true })).toBeFocused();
  await noOverflow(page);
  await page.screenshot({
    path: info.outputPath("phone-entry.png"),
    fullPage: true,
  });
  await enterPhone(page);
  await expect(page.getByLabel("Six-digit code")).toHaveAttribute(
    "autocomplete",
    "one-time-code",
  );
  await expect(
    page.getByRole("button", { name: "Resend in 60s" }),
  ).toBeDisabled();
  await noOverflow(page);
  await page.screenshot({
    path: info.outputPath("otp-verification.png"),
    fullPage: true,
  });
  await page.getByLabel("Six-digit code").fill("654321");
  await expect(page).toHaveURL(/\/app$/);
  expect(api.verificationCount()).toBe(1);
  await expect(page.getByTestId("repair-charger-btn")).toBeVisible();
  await noOverflow(page);
  await page.screenshot({
    path: info.outputPath("successful-login.png"),
    fullPage: true,
  });
});

test("new customer returns to repair and explicitly opts into WhatsApp", async ({
  page,
}) => {
  const api = await mockApi(page, { newCustomer: true });
  await page.goto("/repairs/new");
  await expect(page).toHaveURL(/\/login$/);
  await enterPhone(page);
  await page.getByLabel("Six-digit code").fill("654321");
  await expect(page.getByLabel("Full name")).toBeFocused();
  await page.getByLabel("Full name").fill("Test Customer");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/repairs\/new$/);
  await expect(page.getByTestId("whatsapp-opt-in")).not.toBeChecked();
  await page.getByTestId("brand-input").fill("Test brand");
  await page.getByTestId("model-input").fill("Test model");
  await page.getByTestId("type-select").click();
  await page.getByRole("option", { name: "AC Charger", exact: true }).click();
  await page.getByTestId("description-input").fill("Synthetic repair test.");
  await page.getByTestId("whatsapp-opt-in").check();
  await page.getByTestId("submit-repair-btn").click();
  await expect.poll(() => api.repair()?.whatsapp_opt_in).toBe(true);
  await noOverflow(page);
});

test("Google customer links phone without automatic consent", async ({
  page,
}) => {
  const api = await mockApi(page, {
    initial: { ...customer, phone: "", phone_verified: false },
  });
  await page.goto("/repairs/new");
  await expect(page.getByTestId("whatsapp-opt-in")).toHaveCount(0);
  await page.getByRole("button", { name: "Add and verify phone" }).click();
  await enterPhone(page);
  await page.getByLabel("Six-digit code").fill("654321");
  await expect(page.getByTestId("whatsapp-opt-in")).toBeVisible();
  await expect(page.getByTestId("whatsapp-opt-in")).not.toBeChecked();
  expect(api.verificationCount()).toBe(1);
  await noOverflow(page);
});

test("unavailable provider keeps phone entry and clear error", async ({
  page,
}) => {
  await mockApi(page, { unavailable: true });
  await page.goto("/login");
  await page.getByLabel("Mobile number", { exact: true }).fill("9876543210");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "SMS delivery is unavailable",
  );
  await expect(page.getByLabel("Six-digit code")).toHaveCount(0);
  await noOverflow(page);
});

test("wrong code is not automatically retried and can be edited", async ({
  page,
}) => {
  const api = await mockApi(page);
  await page.goto("/login");
  await enterPhone(page);
  await page.getByLabel("Six-digit code").fill("000000");
  await expect(page.getByRole("alert")).toContainText("Incorrect, expired");
  await page.getByRole("button", { name: "Verify code", exact: true }).click();
  expect(api.verificationCount()).toBe(1);
  await page.getByLabel("Six-digit code").fill("654321");
  await expect(page).toHaveURL(/\/app$/);
  expect(api.verificationCount()).toBe(2);
});

test("Google alternative starts a document navigation", async ({ page }) => {
  await mockApi(page);
  let documentNavigation = false;
  await page.route("**/api/auth/google/login", async (route) => {
    documentNavigation = route.request().isNavigationRequest();
    await route.fulfill({
      contentType: "text/html",
      body: "<h1>Mock Google sign-in</h1>",
    });
  });
  await page.goto("/login");
  await page.getByRole("button", { name: "Continue with Google" }).click();
  await expect(
    page.getByRole("heading", { name: "Mock Google sign-in" }),
  ).toBeVisible();
  expect(documentNavigation).toBe(true);
});

test("account page links the existing Google identity", async ({ page }) => {
  await mockApi(page, {
    initial: { ...customer, phone: "", phone_verified: false },
  });
  await page.goto("/app/phone");
  await enterPhone(page);
  await page.getByLabel("Six-digit code").fill("654321");
  await expect(page.getByRole("status")).toContainText(
    "Your mobile number is verified",
  );
  await expect(page).toHaveURL(/\/app\/phone$/);
  await noOverflow(page);
});

test("phone conflict gives recovery guidance without shifting controls", async ({
  page,
}) => {
  await mockApi(page, {
    initial: { ...customer, phone: "", phone_verified: false },
  });
  await page.route("**/api/auth/phone/verify-otp", (route) =>
    route.fulfill({ status: 409, json: { detail: "Already linked" } }),
  );
  await page.goto("/app/phone");
  await enterPhone(page);
  const edit = page.getByTestId("change-phone-btn");
  const before = await edit.boundingBox();
  await page.getByLabel("Six-digit code").fill("654321");
  await expect(page.getByRole("alert")).toContainText("account recovery");
  const after = await edit.boundingBox();
  expect(after.y).toBeCloseTo(before.y, 0);
  await noOverflow(page);
});
