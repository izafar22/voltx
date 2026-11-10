import React from "react";
import { render, screen } from "@testing-library/react";
import WhatsAppChatLink, { WHATSAPP_CHAT_URL } from "./WhatsAppChatLink";

test("opens the correct RushX WhatsApp chat in a new tab", () => {
  render(<WhatsAppChatLink />);
  const link = screen.getByRole("link", { name: /chat with rushx on whatsapp/i });
  expect(link).toHaveAttribute("href", WHATSAPP_CHAT_URL);
  expect(link).toHaveAttribute("target", "_blank");
  expect(link).toHaveAttribute("rel", "noopener noreferrer");
  const url = new URL(link.href);
  expect(url.hostname).toBe("wa.me");
  expect(url.pathname).toBe("/918528077908");
  expect(url.searchParams.get("text")).toContain("EV charger repair");
});
