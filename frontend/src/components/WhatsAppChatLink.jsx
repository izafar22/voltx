import React from "react";

// Public customer support number. WhatsApp click-to-chat does not use Cloud API
// credentials, OTP flows, or the backend WhatsApp outbox.
const WHATSAPP_NUMBER = "918528077908";
const MESSAGE = "Hi RushX, I need help with my EV charger repair. Can you assist me?";
export const WHATSAPP_CHAT_URL = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(MESSAGE)}`;

export default function WhatsAppChatLink() {
  return (
    <a
      href={WHATSAPP_CHAT_URL}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Chat with RushX on WhatsApp (opens a new tab)"
      title="Chat with RushX on WhatsApp"
      className="fixed bottom-6 right-6 z-50 flex h-[var(--whatsapp-chat-size)] w-[var(--whatsapp-chat-size)] items-center justify-center rounded-full bg-whatsapp-chat-background text-whatsapp-chat-foreground shadow-whatsapp-chat transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      data-testid="whatsapp-chat-link"
    >
      <svg aria-hidden="true" viewBox="0 0 32 32" className="h-[var(--whatsapp-chat-icon-size)] w-[var(--whatsapp-chat-icon-size)] fill-whatsapp-chat-foreground">
        <path d="M16 .8A15.1 15.1 0 0 0 3 23.6L.9 31l7.6-2A15.2 15.2 0 1 0 16 .8Zm0 27.5a12.4 12.4 0 0 1-6.3-1.7l-.5-.3-4.5 1.2 1.2-4.4-.3-.5A12.4 12.4 0 1 1 16 28.3Zm6.8-9.3c-.4-.2-2.2-1.1-2.5-1.2-.3-.1-.6-.2-.8.2-.3.4-1 1.2-1.2 1.4-.2.2-.4.3-.8.1-.4-.2-1.6-.6-3-1.9-1.1-1-1.9-2.2-2.1-2.6-.2-.4 0-.6.2-.8l.6-.7.4-.6c.1-.2.1-.5 0-.7l-1.1-2.7c-.3-.7-.6-.6-.8-.6h-.7c-.3 0-.7.1-1 .5-.4.4-1.3 1.3-1.3 3.1s1.3 3.5 1.5 3.8c.2.2 2.6 4 6.4 5.5.9.4 1.6.6 2.1.8.9.3 1.7.2 2.4.1.7-.1 2.2-.9 2.5-1.8.3-.9.3-1.7.2-1.8-.1-.2-.3-.3-.7-.5Z" />
      </svg>
    </a>
  );
}
