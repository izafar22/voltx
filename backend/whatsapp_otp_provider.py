"""Meta WhatsApp Cloud API OTP provider for explicitly allowlisted staging recipients."""
import os
import httpx
from fastapi import HTTPException


class WhatsAppOtpProvider:
    def __init__(self, *, token, phone_number_id, recipients, template, version="v25.0"):
        self.token = token
        self.phone_number_id = phone_number_id
        self.recipients = frozenset(recipients)
        self.template = template
        self.version = version

    @classmethod
    def from_env(cls):
        return cls(
            token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
            phone_number_id=os.getenv("WHATSAPP_TEST_PHONE_NUMBER_ID", ""),
            recipients=[x.strip() for x in os.getenv("WHATSAPP_TEST_RECIPIENTS", "").split(",") if x.strip()],
            template=os.getenv("WHATSAPP_AUTH_TEMPLATE", "rushx_authentication_otp_v1"),
            version=os.getenv("WHATSAPP_API_VERSION", "v25.0"),
        )

    async def send_otp(self, phone, code):
        if not self.token or not self.phone_number_id or not self.recipients:
            raise HTTPException(503, "WhatsApp OTP is not configured")
        if phone not in self.recipients:
            raise HTTPException(403, "Phone is not an authorized staging test recipient")
        if not self.version.startswith("v") or not self.version[1:].replace(".", "").isdigit():
            raise HTTPException(503, "Invalid WhatsApp API version")
        payload = {
            "messaging_product": "whatsapp",
            "to": phone.removeprefix("+"),
            "type": "template",
            "template": {
                "name": self.template,
                "language": {"code": "en_US"},
                "components": [{"type": "body", "parameters": [{"type": "text", "text": code}]},
                    {"type": "button", "sub_type": "url", "index": "0",
                     "parameters": [{"type": "text", "text": code}]}],
            },
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"https://graph.facebook.com/{self.version}/{self.phone_number_id}/messages",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json=payload,
                )
            response.raise_for_status()
        except httpx.HTTPError:
            raise HTTPException(503, "WhatsApp OTP delivery failed") from None
