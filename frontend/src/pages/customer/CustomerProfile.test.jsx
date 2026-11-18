import React, { act } from "react";
import { createRoot } from "react-dom/client";
import CustomerProfile from "./CustomerProfile";
import { CustomerAddressEditor } from "../../components/CustomerAddressEditor";
import { CustomerPhoneLink } from "../../components/CustomerPhoneLink";
const mockPost = jest.fn(),
  mockPatch = jest.fn(),
  mockSetUser = jest.fn(),
  mockSetData = jest.fn(),
  mockCancel = jest.fn(),
  mockDelete = jest.fn();
let mockProfile, mockQueryError, mockParams, mockGeneration;
jest.mock(
  "react-router-dom",
  () => ({ useSearchParams: () => [new URLSearchParams(mockParams)] }),
  { virtual: true },
);
jest.mock("@tanstack/react-query", () => ({
  useQuery: () => ({
    data: mockProfile,
    isError: mockQueryError,
    refetch: jest.fn(),
  }),
  useQueryClient: () => ({
    setQueryData: mockSetData,
    cancelQueries: mockCancel,
  }),
}));
jest.mock("../../lib/api", () => ({
  api: {
    post: (...args) => mockPost(...args),
    patch: (...args) => mockPatch(...args),
    delete: (...args) => mockDelete(...args),
  },
}));
jest.mock("../../context/AuthContext", () => ({
  useAuth: () => ({
    user: mockProfile.user,
    beginUserUpdate: () => {
      const started = mockGeneration;
      return (next) => {
        if (started !== mockGeneration) return false;
        mockSetUser(next);
        return true;
      };
    },
  }),
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
  mockCancel.mockResolvedValue();
  mockQueryError = false;
  mockParams = "";
  mockGeneration = 0;
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
  const checks = ["Default pickup address", "Default delivery address"].map(
    (text) => {
      const label = [...document.querySelectorAll("label")].find(
        (node) => node.textContent.trim() === text,
      );
      expect(label).toBeDefined();
      const control = label.querySelector("input[type=checkbox]");
      expect(control).not.toBeNull();
      expect(control.checked).toBe(true);
      return control;
    },
  );
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
  expect(saved).toHaveBeenCalledWith(mockProfile, undefined);
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
  expect(mockPost).toHaveBeenNthCalledWith(2, "/auth/link/phone/verify", {
    phone: "9876543210",
    otp: "123456",
    challenge_id: "test-challenge",
  });
  expect(document.querySelector("[role=alert]").textContent).toContain(
    "already linked",
  );
  expect(document.querySelector("#link-phone").value).toBe("9876543210");
  expect(saved).not.toHaveBeenCalled();
});
const renderProfile = () => act(() => root.render(<CustomerProfile />));
const button = (text) =>
  [...document.querySelectorAll("button")].find(
    (el) => el.textContent === text,
  );
test.each(["__proto__", "constructor", "toString", "unknown"])(
  "unknown callback status %s cannot crash the profile",
  (status) => {
    mockParams = `google_link=${status}`;
    renderProfile();
    expect(container.textContent).toContain("Your profile");
  },
);
test("dirty name survives refresh and typing during a pending save", async () => {
  renderProfile();
  fill("profile-name", "My draft");
  mockProfile = {
    ...mockProfile,
    user: { ...mockProfile.user, name: "Other tab" },
  };
  renderProfile();
  expect(document.getElementById("profile-name").value).toBe("My draft");
  let resolve;
  mockPatch.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  await submit();
  fill("profile-name", "Still typing");
  await act(async () =>
    resolve({
      data: { ...mockProfile, user: { ...mockProfile.user, name: "My draft" } },
    }),
  );
  expect(document.getElementById("profile-name").value).toBe("Still typing");
});
test("delayed name save cannot restore a different session and cancels old reads first", async () => {
  renderProfile();
  fill("profile-name", "Draft");
  let resolve;
  mockPatch.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  await submit();
  mockGeneration += 1;
  await act(async () => resolve({ data: mockProfile }));
  expect(mockCancel).toHaveBeenCalledWith({
    queryKey: ["customer-profile", "test"],
    exact: true,
  });
  expect(mockSetUser).not.toHaveBeenCalled();
  expect(mockSetData).not.toHaveBeenCalled();
});
test("background error preserves an open address draft and its original revision", async () => {
  renderProfile();
  act(() => button("Add address").click());
  fill("address-line1", "Draft street");
  mockQueryError = true;
  mockProfile = { ...mockProfile, revision: 1 };
  renderProfile();
  expect(document.getElementById("address-line1").value).toBe("Draft street");
  expect(document.body.textContent).toContain("Your draft is preserved");
  mockPost.mockRejectedValue({
    response: { status: 409, data: { detail: "stale" } },
  });
  const form = document.getElementById("address-line1").closest("form");
  await act(async () =>
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    ),
  );
  expect(mockPost).toHaveBeenCalledWith(
    "/customer/addresses",
    expect.objectContaining({ revision: 0 }),
  );
  expect(document.getElementById("address-line1").value).toBe("Draft street");
});
test("delete choices require review after a background revision change", async () => {
  const addresses = ["A", "B", "C"].map((id) => ({
    id,
    label: id,
    line1: "Test street",
  }));
  mockProfile = { ...mockProfile, addresses, pickup_id: "B", revision: 2 };
  renderProfile();
  act(() => button("Delete C").click());
  mockProfile = { ...mockProfile, pickup_id: "A", revision: 3 };
  renderProfile();
  expect(button("Confirm deletion").disabled).toBe(true);
  expect(mockDelete).not.toHaveBeenCalled();
  act(() => button("Reload deletion choices").click());
  mockDelete.mockResolvedValue({ data: mockProfile });
  await act(async () => button("Confirm deletion").click());
  expect(mockDelete).toHaveBeenCalledWith("/customer/addresses/C", {
    data: { revision: 3, pickup_id: "A", delivery_id: null },
  });
});
test("phone verification merges user into the latest cached profile", async () => {
  renderProfile();
  act(() => button("Add and verify mobile number").click());
  fill("link-phone", "9876543210");
  mockPost.mockResolvedValueOnce({
    data: { challenge_id: "challenge", resend_after: 60 },
  });
  await act(async () =>
    document
      .getElementById("link-phone")
      .closest("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })),
  );
  fill("link-otp", "123456");
  let resolve;
  mockPost.mockReturnValueOnce(
    new Promise((done) => {
      resolve = done;
    }),
  );
  await act(async () =>
    document
      .getElementById("link-otp")
      .closest("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })),
  );
  const latest = { ...mockProfile, addresses: [{ id: "new" }], revision: 4 };
  await act(async () =>
    resolve({ data: { user: { ...mockProfile.user, phone_verified: true } } }),
  );
  const updater = mockSetData.mock.calls[0][1];
  expect(updater(latest)).toEqual({
    ...latest,
    user: { ...mockProfile.user, phone_verified: true },
  });
  expect(mockCancel.mock.invocationCallOrder[0]).toBeLessThan(
    mockSetData.mock.invocationCallOrder[0],
  );
});
