"""Deliver OTPs through an approved WhatsApp Cloud API authentication template."""
import os
import re
import httpx

class WhatsAppOtpProvider:
    def __init__(self):
        self.token = os.environ["WHATSAPP_ACCESS_TOKEN"]
        self.phone_number_id = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
        self.template = os.getenv("WHATSAPP_OTP_TEMPLATE", "rushx_authentication_otp")
        self.language = os.getenv("WHATSAPP_OTP_LANGUAGE", "en_US")
        self.version = os.getenv("WHATSAPP_API_VERSION", "v25.0")
        if not self.token or not re.fullmatch(r"[0-9]+", self.phone_number_id):
            raise RuntimeError("Invalid WhatsApp OTP credentials")
        if not re.fullmatch(r"v[0-9]+\.[0-9]+", self.version):
            raise RuntimeError("Invalid WhatsApp API version")

    async def send_otp(self, phone: str, code: str):
        payload = {
            "messaging_product": "whatsapp", "to": phone.lstrip("+"), "type": "template",
            "template": {
                "name": self.template, "language": {"code": self.language},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": code}]},
                    {"type": "button", "sub_type": "url", "index": "0",
                     "parameters": [{"type": "text", "text": code}]},
                ],
            },
        }
        url = f"https://graph.facebook.com/{self.version}/{self.phone_number_id}/messages"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload,
                                         headers={"Authorization": f"Bearer {self.token}"})
            response.raise_for_status()
