import { WHATSAPP_CHAT_URL } from "./WhatsAppChatLink";

test("points to the correct RushX WhatsApp number with a repair enquiry", () => {
  const url = new URL(WHATSAPP_CHAT_URL);
  expect(url.protocol).toBe("https:");
  expect(url.hostname).toBe("wa.me");
  expect(url.pathname).toBe("/918528077908");
  expect(url.searchParams.get("text")).toContain("EV charger repair");
});
