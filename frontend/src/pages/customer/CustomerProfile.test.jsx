import React, { act } from "react";
import { createRoot } from "react-dom/client";
import CustomerProfile from "./CustomerProfile";
import { CustomerAddressEditor } from "../../components/CustomerAddressEditor";
import { CustomerPhoneLink } from "../../components/CustomerPhoneLink";
const mockPost = jest.fn(),
  mockPatch = jest.fn(),
  mockSetUser = jest.fn(),
  mockSetData = jest.fn();
let mockProfile;
jest.mock(
  "react-router-dom",
  () => ({ useSearchParams: () => [new URLSearchParams()] }),
  { virtual: true },
);
jest.mock("@tanstack/react-query", () => ({
  useQuery: () => ({ data: mockProfile }),
  useQueryClient: () => ({ setQueryData: mockSetData }),
}));
jest.mock("../../lib/api", () => ({
  api: {
    post: (...args) => mockPost(...args),
    patch: (...args) => mockPatch(...args),
  },
}));
jest.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ user: mockProfile.user, setUser: mockSetUser }),
}));
jest.mock("../../components/layout/CustomerShell", () => ({
  CustomerShell: ({ children }) => <main>{children}</main>,
}));
jest.mock(
  "@/lib/utils",
  () => ({ cn: (...classes) => classes.filter(Boolean).join(" ") }),
  { virtual: true },
);
let root, container;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  mockProfile = {
    user: {
      user_id: "test",
      name: "Test Customer",
      google_linked: true,
      email: "test@example.com",
      phone_verified: false,
    },
    addresses: [],
    pickup_id: null,
    delivery_id: null,
    revision: 0,
  };
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => {
  act(() => root.unmount());
  container.remove();
});
const fill = (id, value) =>
  act(() => {
    const input = document.getElementById(id);
    Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    ).set.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
const submit = async () =>
  act(async () => {
    document
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
test("read-only verified email and name edit update shared profile state", async () => {
  act(() => root.render(<CustomerProfile />));
  expect(container.textContent).toContain("test@example.com");
  expect(container.querySelector("input[type=email]")).toBeNull();
  expect(container.textContent).toContain("You can sign in with Google.");
  fill("profile-name", "Updated Customer");
  const next = {
    ...mockProfile,
    user: { ...mockProfile.user, name: "Updated Customer" },
  };
  mockPatch.mockResolvedValue({ data: next });
  await submit();
  expect(mockPatch).toHaveBeenCalledWith("/customer/profile", {
    name: "Updated Customer",
  });
  expect(mockSetUser).toHaveBeenCalledWith(next.user);
  expect(container.textContent).toContain("Changes saved.");
});
test("first address preselects defaults but allows both to be cleared", async () => {
  const saved = jest.fn();
  act(() =>
    root.render(
      <CustomerAddressEditor
        profile={mockProfile}
        onSaved={saved}
        onClose={jest.fn()}
      />,
    ),
  );
  const checks = [...document.querySelectorAll("input[type=checkbox]")];
  expect(checks.every((c) => c.checked)).toBe(true);
  act(() => checks.forEach((c) => c.click()));
  for (const [key, value] of Object.entries({
    label: "Home",
    line1: "Test building",
    city: "Test city",
    state: "Test state",
    pin: "123456",
  }))
    fill(`address-${key}`, value);
  mockPost.mockResolvedValue({ data: mockProfile });
  await submit();
  expect(mockPost).toHaveBeenCalledWith(
    "/customer/addresses",
    expect.objectContaining({
      revision: 0,
      default_pickup: false,
      default_delivery: false,
      country: "India",
    }),
  );
  expect(saved).toHaveBeenCalledWith(mockProfile);
});
test("WhatsApp conflict retains dialog and current account", async () => {
  const saved = jest.fn();
  act(() =>
    root.render(
      <CustomerPhoneLink hasPhone onSaved={saved} onClose={jest.fn()} />,
    ),
  );
  fill("link-phone", "9876543210");
  mockPost.mockResolvedValueOnce({
    data: { challenge_id: "test-challenge", resend_after: 60 },
  });
  await submit();
  fill("link-otp", "123456");
  mockPost.mockRejectedValueOnce({
    response: {
      status: 409,
      data: {
        detail: {
          message:
            "This mobile number is already linked to another RushX account. Use a different number.",
        },
      },
    },
  });
  await submit();
  expect(document.querySelector("[role=alert]").textContent).toContain(
    "already linked",
  );
  expect(document.querySelector("#link-phone").value).toBe("9876543210");
  expect(saved).not.toHaveBeenCalled();
});
