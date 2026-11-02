"""Delivery-only SMS adapter; RushX remains the sole OTP verification authority.
Contract: https://docs.msg91.com/sms/send-sms (reviewed 2026-11-03).
"""
import os
import re
from dataclasses import dataclass, field

import httpx


class SmsDeliveryError(Exception):
    """Intentionally excludes provider response/request details and credentials."""


@dataclass(frozen=True)
class Msg91Settings:
    auth_key: str = field(repr=False)
    template_id: str
    sender_id: str
    otp_variable: str

    @classmethod
    def from_env(cls):
        settings = cls(*(os.getenv(key, '').strip() for key in (
            'MSG91_AUTH_KEY', 'MSG91_TEMPLATE_ID', 'MSG91_SENDER_ID', 'MSG91_OTP_VARIABLE')))
        if (not settings.auth_key or re.search(r'\s', settings.auth_key)
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', settings.template_id)
                or not re.fullmatch(r'[A-Za-z]{6}', settings.sender_id)
                or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', settings.otp_variable)
                or settings.otp_variable.lower() == 'mobiles'):
            raise ValueError('Incomplete SMS configuration')
        return settings


class Msg91OtpProvider:
    endpoint = 'https://control.msg91.com/api/v5/flow'

    def __init__(self, settings, transport=None):
        self.settings, self.transport = settings, transport

    async def send_otp(self, phone, code):
        if not re.fullmatch(r'\+91[6-9][0-9]{9}', phone) or not re.fullmatch(r'[0-9]{6}', code):
            raise SmsDeliveryError('SMS delivery unavailable')
        # Sender/DLT/PE binding is configured in the MSG91 template, not an
        # undocumented sender parameter on the current template_id SMS API.
        payload = {'template_id': self.settings.template_id, 'short_url': '0',
                   'recipients': [{'mobiles': phone[1:], self.settings.otp_variable: code}]}
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10, connect=3, read=10, write=5, pool=3),
                follow_redirects=False, trust_env=False, transport=self.transport,
            ) as client:
                response = await client.post(self.endpoint, json=payload,
                    headers={'authkey': self.settings.auth_key, 'accept': 'application/json'})
                if response.status_code != 200:
                    raise SmsDeliveryError('SMS delivery unavailable')
                body = response.json()
                if (not isinstance(body, dict) or body.get('type') != 'success'
                        or not isinstance(body.get('message'), str) or not body['message'].strip()):
                    raise SmsDeliveryError('SMS delivery unavailable')
        except (httpx.HTTPError, ValueError, TypeError):
            # No retries: a timeout can mean accepted delivery with a lost response.
            # Never log request bodies, auth headers, codes, or provider responses.
            raise SmsDeliveryError('SMS delivery unavailable') from None
