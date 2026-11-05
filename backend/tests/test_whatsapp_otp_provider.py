"""Offline contract tests for WhatsApp OTP transport (no Meta requests)."""
import asyncio
import json
from unittest.mock import patch
import httpx
import pytest
from whatsapp_otp_provider import WhatsAppOtpProvider

def make_provider(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "1381664668361854")
    monkeypatch.setenv("WHATSAPP_API_VERSION", "v27.0")
    monkeypatch.setenv("WHATSAPP_OTP_TEMPLATE", "rushx_authentication_otp")
    monkeypatch.setenv("WHATSAPP_OTP_LANGUAGE", "en_US")
    return WhatsAppOtpProvider()

def test_otp_template_payload(monkeypatch):
    provider = make_provider(monkeypatch)
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.test"}]})
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient
    def fake_client(*args, **kwargs):
        return real_client(*args, transport=transport, **kwargs)
    with patch("whatsapp_otp_provider.httpx.AsyncClient", side_effect=fake_client):
        asyncio.run(provider.send_otp("+917982237681", "654321"))
    assert len(calls) == 1
    request = calls[0]
    assert str(request.url) == "https://graph.facebook.com/v27.0/1381664668361854/messages"
    assert request.headers["Authorization"] == "Bearer test-token"
    body = json.loads(request.content)
    assert body["to"] == "917982237681"
    assert body["template"]["name"] == "rushx_authentication_otp"
    assert body["template"]["language"]["code"] == "en_US"
    assert body["template"]["components"] == [
        {"type": "body", "parameters": [{"type": "text", "text": "654321"}]},
        {"type": "button", "sub_type": "url", "index": "0",
         "parameters": [{"type": "text", "text": "654321"}]},
    ]

def test_meta_error_fails_closed(monkeypatch):
    provider = make_provider(monkeypatch)
    real_client = httpx.AsyncClient
    with patch("whatsapp_otp_provider.httpx.AsyncClient",
               side_effect=lambda *a, **kw: real_client(*a, transport=httpx.MockTransport(
                   lambda request: httpx.Response(400, json={"error": {"message": "Invalid template"}})), **kw)):
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(provider.send_otp("+917982237681", "654321"))
