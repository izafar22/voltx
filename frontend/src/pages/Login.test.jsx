import React, { act } from "react";
import { createRoot } from "react-dom/client";
import Login from "./Login";
const mockPost = jest.fn(),
  mockLogin = jest.fn(),
  mockNavigate = jest.fn();
let mockAuth, mockState;
jest.mock("../lib/api", () => ({
  api: { post: (...args) => mockPost(...args) },
}));
jest.mock("../context/AuthContext", () => ({ useAuth: () => mockAuth }));
jest.mock("../components/ProtectedRoute", () => ({
  homeFor: (role) =>
    role === "admin" ? "/admin" : role === "owner" ? "/owner" : "/app",
}));
jest.mock(
  "react-router-dom",
  () => ({
    useNavigate: () => mockNavigate,
    useLocation: () => ({ state: mockState }),
    Navigate: ({ to }) => <span data-redirect={to} />,
  }),
  { virtual: true },
);
jest.mock("../components/Logo", () => ({ Logo: () => <span>RushX</span> }));
let root, container;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  process.env.REACT_APP_DEMO_AUTH = "false";
  mockState = null;
  sessionStorage.clear();
  mockAuth = { user: null, loading: false, login: mockLogin };
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => {
  act(() => root.unmount());
  container.remove();
  jest.useRealTimers();
  window.history.replaceState({}, "", "/login");
});
const render = () => act(() => root.render(<Login />));
const fill = (id, value) =>
  act(() => {
    const n = container.querySelector("#" + id);
    Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    ).set.call(n, value);
    n.dispatchEvent(new Event("input", { bubbles: true }));
  });
const settle = () =>
  act(async () => {
    await Promise.resolve();
  });
const submit = () =>
  act(async () => {
    container
      .querySelector("form")
      ?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
async function request() {
  mockPost.mockResolvedValueOnce({
    data: { challenge_id: "challenge", resend_after: 60 },
  });
  render();
  fill("phone", "98765 43210");
  await submit();
}
test("phone-first screen has one Continue, default country code and Google alternative", () => {
  render();
  expect(container.textContent).toContain("+91");
  expect(container.querySelector("#full-name")).toBeNull();
  expect(container.textContent).not.toContain("Development demo");
  expect(
    [...container.querySelectorAll("button")].some(
      (b) => b.textContent === "Continue",
    ),
  ).toBe(true);
  expect(container.textContent).toContain("Continue with Google");
  expect(document.activeElement.id).toBe("phone");
});
test("invalid phone stays on phone entry", async () => {
  render();
  fill("phone", "123");
  await submit();
  expect(mockPost).not.toHaveBeenCalled();
  expect(container.querySelector("[role=alert]").textContent).toContain(
    "valid 10-digit",
  );
});
test("normalizes number, masks destination and supports OTP autofill", async () => {
  await request();
  expect(mockPost).toHaveBeenCalledWith("/auth/request-otp", {
    phone: "+919876543210",
  });
  expect(container.textContent).toContain("+91••••••3210");
  expect(container.querySelector("#otp").autocomplete).toBe("one-time-code");
  expect(document.activeElement.id).toBe("otp");
});
test("six digits automatically submit exactly once and restore intended destination", async () => {
  mockState = { from: "/repairs/new" };
  await request();
  const user = { role: "customer" };
  mockPost.mockResolvedValueOnce({ data: { user } });
  fill("otp", "654321");
  await settle();
  await submit();
  expect(mockPost).toHaveBeenCalledTimes(2);
  expect(mockPost).toHaveBeenLastCalledWith("/auth/verify-otp", {
    phone: "+919876543210",
    challenge_id: "challenge",
    otp: "654321",
  });
  expect(mockLogin).toHaveBeenCalledWith(user);
  expect(mockNavigate).toHaveBeenCalledWith("/repairs/new", { replace: true });
});
test("full-code paste submits and duplicate requests stay locked", async () => {
  await request();
  let resolve;
  mockPost.mockImplementationOnce(() => new Promise((r) => (resolve = r)));
  act(() => {
    const event = new Event("paste", { bubbles: true, cancelable: true });
    Object.defineProperty(event, "clipboardData", {
      value: { getData: () => "654321" },
    });
    container.querySelector("#otp").dispatchEvent(event);
  });
  await submit();
  await submit();
  expect(mockPost).toHaveBeenCalledTimes(2);
  await act(async () => resolve({ data: { user: { role: "customer" } } }));
});
test("new customer provides only a name", async () => {
  await request();
  mockPost.mockResolvedValueOnce({
    data: { registration_required: true, registration_token: "grant" },
  });
  fill("otp", "654321");
  await settle();
  expect(container.querySelector("#email")).toBeNull();
  expect(document.activeElement.id).toBe("full-name");
  fill("full-name", " ");
  await submit();
  expect(container.textContent).toContain("Enter your full name");
  fill("full-name", " Test Customer ");
  mockPost.mockResolvedValueOnce({ data: { user: { role: "customer" } } });
  await submit();
  expect(mockPost).toHaveBeenLastCalledWith(
    "/auth/register-customer",
    { name: "Test Customer", email: "" },
    { headers: { Authorization: "Bearer grant" } },
  );
});
test.each([400, 429, 503])(
  "verification error %s is clear and does not resubmit on timer ticks",
  async (status) => {
    jest.useFakeTimers();
    await request();
    mockPost.mockRejectedValueOnce({
      response: { status, data: { detail: "private diagnostic" } },
    });
    fill("otp", "000000");
    await settle();
    act(() => jest.advanceTimersByTime(10000));
    await settle();
    expect(mockPost).toHaveBeenCalledTimes(2);
    expect(container.querySelector("[role=alert]")).not.toBeNull();
    expect(container.textContent).not.toContain("private diagnostic");
    expect(mockLogin).not.toHaveBeenCalled();
  },
);
test("provider unavailable never claims SMS sent", async () => {
  render();
  fill("phone", "9876543210");
  mockPost.mockRejectedValueOnce({ response: { status: 503 } });
  await submit();
  expect(container.querySelector("#otp")).toBeNull();
  expect(container.textContent).toContain("SMS delivery is unavailable");
  expect(container.textContent).not.toContain("Code sent");
});
test("resend counts down and editing a number returns focus", async () => {
  jest.useFakeTimers();
  await request();
  expect(
    [...container.querySelectorAll("button")].find(
      (b) => b.textContent === "Resend in 60s",
    ).disabled,
  ).toBe(true);
  act(() => jest.advanceTimersByTime(60000));
  mockPost.mockResolvedValueOnce({
    data: { challenge_id: "new", resend_after: 60 },
  });
  await act(async () =>
    [...container.querySelectorAll("button")]
      .find((b) => b.textContent === "Resend code")
      .click(),
  );
  expect(mockPost).toHaveBeenCalledTimes(2);
  act(() => container.querySelector("[data-testid=change-phone-btn]").click());
  expect(document.activeElement.id).toBe("phone");
});
test("Google uses top-level navigation and remembers a safe destination", () => {
  const original = window.location;
  const assign = jest.fn();
  delete window.location;
  window.location = { assign, search: "" };
  try {
    mockState = { from: "/repairs/new" };
    render();
    act(() =>
      [...container.querySelectorAll("button")]
        .find((b) => b.textContent.includes("Continue with Google"))
        .click(),
    );
    expect(assign).toHaveBeenCalledWith("/api/auth/google/login");
    expect(sessionStorage.getItem("rushx.auth.returnTo")).toBe("/repairs/new");
    expect(mockPost).not.toHaveBeenCalled();
  } finally {
    window.location = original;
  }
});
test.each([
  "//evil.example",
  "https://evil.example",
  "/\\evil",
  "/login",
  "/app/../evil",
])("unsafe destination %s falls back", async (from) => {
  mockState = { from };
  await request();
  mockPost.mockResolvedValueOnce({ data: { user: { role: "customer" } } });
  fill("otp", "654321");
  await settle();
  expect(mockNavigate).toHaveBeenCalledWith("/app", { replace: true });
});
test("Google callback reload restores the remembered path", () => {
  sessionStorage.setItem("rushx.auth.returnTo", "/repairs/new");
  mockAuth.user = { role: "customer" };
  render();
  expect(
    container.querySelector("[data-redirect]").getAttribute("data-redirect"),
  ).toBe("/repairs/new");
  expect(sessionStorage.getItem("rushx.auth.returnTo")).toBeNull();
});
test("Google error leaves SMS available", () => {
  window.history.replaceState({}, "", "/login?google_error=1");
  render();
  expect(container.querySelector("[role=alert]").textContent).toContain(
    "Google sign-in could not be completed",
  );
  expect(container.querySelector("#phone")).not.toBeNull();
});
