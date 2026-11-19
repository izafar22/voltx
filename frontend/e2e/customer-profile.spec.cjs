const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

for (const theme of ["light", "dark"])
  for (const identity of ["google", "whatsapp", "both"]) {
    test(`customer profile ${identity} ${theme}: persistence, full repair form and saved addresses`, async ({
      page,
    }, info) => {
      let user = {
        user_id: "synthetic-customer",
        role: "customer",
        name: "Example Customer",
        status: "active",
        google_linked: identity !== "whatsapp",
        phone_verified: identity !== "google",
        email: identity !== "whatsapp" ? "customer@example.com" : "",
        phone: identity !== "google" ? "+919876543210" : "",
      };
      let profile = {
        user,
        addresses: [],
        revision: 0,
        pickup_id: null,
        delivery_id: null,
      };
      const errors = [];
      page.on("pageerror", (e) => errors.push(e.message));
      await page.addInitScript((theme) => {
        localStorage.setItem("rushx-theme", theme);
      }, theme);
      await page.route("**/api/**", async (route) => {
        const request = route.request(),
          path = new URL(request.url()).pathname;
        const body = request.postDataJSON();
        if (path === "/api/auth/me") return route.fulfill({ json: user });
        if (path === "/api/customer/profile") {
          if (request.method() === "PATCH") user = { ...user, name: body.name };
          profile.user = user;
          return route.fulfill({ json: profile });
        }
        if (path === "/api/customer/addresses" && request.method() === "POST") {
          const { revision, default_pickup, default_delivery, ...address } =
            body;
          profile = {
            ...profile,
            addresses: [...profile.addresses, { ...address, id: "address-1" }],
            revision: revision + 1,
            pickup_id: default_pickup ? "address-1" : null,
            delivery_id: default_delivery ? "address-1" : null,
          };
          return route.fulfill({ json: profile });
        }
        if (path === "/api/auth/link/phone/request")
          return route.fulfill({
            json: { challenge_id: "test-challenge", resend_after: 60 },
          });
        if (path === "/api/auth/link/phone/verify") {
          user = { ...user, phone_verified: true, phone: "+919876543210" };
          profile.user = user;
          return route.fulfill({ json: { user } });
        }
        if (path === "/api/repairs") return route.fulfill({ json: [] });
        return route.fulfill({
          status: 404,
          json: { detail: "Fixture endpoint unavailable" },
        });
      });
      await page.goto("/app/profile");
      await expect(page.locator("html")).toHaveCSS("color-scheme", theme);
      await expect(
        page.getByRole("heading", { name: "Your profile" }),
      ).toBeVisible();
      await page
        .getByLabel("Full name", { exact: true })
        .fill("Updated Customer");
      await page
        .getByRole("button", { name: "Save name", exact: true })
        .click();
      await expect(page.getByRole("status")).toContainText("Changes saved");
      await page.reload();
      await expect(page.getByLabel("Full name", { exact: true })).toHaveValue(
        "Updated Customer",
      );
      if (identity === "google") {
        await page
          .getByRole("button", { name: "Add and verify mobile number" })
          .click();
        await page
          .getByLabel("Mobile number", { exact: true })
          .fill("9876543210");
        await page.getByRole("button", { name: "Send WhatsApp code" }).click();
        await page.getByLabel("WhatsApp verification code").fill("123456");
        await page.getByRole("button", { name: "Verify and connect" }).click();
        await expect(page.getByRole("dialog")).toHaveCount(0);
        await expect(
          page.getByText("You can sign in with Google or WhatsApp OTP."),
        ).toBeVisible();
      }
      await page
        .getByRole("button", { name: "Add address", exact: true })
        .click();
      for (const [label, value] of [
        ["Label", "Home"],
        ["Address line 1", "Example building"],
        ["City", "Example city"],
        ["State", "Example state"],
        ["PIN code", "123456"],
      ])
        await page.getByLabel(label, { exact: true }).fill(value);
      await page
        .getByRole("button", { name: "Save address", exact: true })
        .click();
      await expect(
        page.getByRole("heading", { name: "Home", exact: true }),
      ).toBeVisible();
      await page.reload();
      await expect(
        page.getByText("Default pickup · Default delivery"),
      ).toBeVisible();
      const accessibility = await new AxeBuilder({ page }).analyze();
      expect(
        accessibility.violations.filter((v) =>
          ["serious", "critical"].includes(v.impact),
        ),
      ).toEqual([]);
      if (info.project.name === "1280")
        await page.getByTestId("nav-repairs").click();
      else {
        await page.getByTestId("menu-btn").click();
        await page
          .getByTestId("mobile-drawer")
          .getByTestId("nav-repairs")
          .click();
      }
      await expect(page).toHaveURL(/\/repairs\/new$/);
      await expect(
        page.getByRole("heading", { name: "1. Choose your charger" }),
      ).toBeVisible();
      await expect(
        page.getByRole("heading", {
          name: "5. Pickup and delivery addresses (optional)",
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        page.getByRole("combobox", { name: "Pickup address", exact: true }),
      ).toContainText("Example building");
      await page.getByLabel("Brand *", { exact: true }).fill("Test brand");
      await page
        .getByRole("button", { name: "Add an address", exact: true })
        .click();
      await page.getByRole("button", { name: "Cancel", exact: true }).click();
      await expect(page.getByLabel("Brand *", { exact: true })).toHaveValue(
        "Test brand",
      );
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBe(true);
      expect(errors).toEqual([]);
    });
  }
