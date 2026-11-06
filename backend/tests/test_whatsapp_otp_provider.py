import pytest
from fastapi import HTTPException
from whatsapp_otp_provider import WhatsAppOtpProvider


@pytest.mark.asyncio
async def test_missing_credentials_fail_closed():
    provider = WhatsAppOtpProvider(token="", phone_number_id="123", recipients=["+919999999999"], template="rushx_authentication_otp_v1")
    with pytest.raises(HTTPException) as exc:
        await provider.send_otp("+919999999999", "123456")
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_unlisted_recipient_rejected_before_network():
    provider = WhatsAppOtpProvider(token="secret", phone_number_id="123", recipients=["+919999999999"], template="rushx_authentication_otp_v1")
    with pytest.raises(HTTPException) as exc:
        await provider.send_otp("+918888888888", "123456")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_provider_posts_otp_template(monkeypatch):
    import httpx
    seen = {}
    async def fake_post(self, url, **kwargs):
        seen.update(url=url, kwargs=kwargs)
        return httpx.Response(200, request=httpx.Request("POST", url), json={"messages": [{"id": "test"}]})
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = WhatsAppOtpProvider(token="secret", phone_number_id="123", recipients=["+919999999999"], template="rushx_authentication_otp_v1")
    await provider.send_otp("+919999999999", "123456")
    assert seen["url"] == "https://graph.facebook.com/v25.0/123/messages"
    assert seen["kwargs"]["json"]["template"]["name"] == "rushx_authentication_otp_v1"
    assert seen["kwargs"]["json"]["template"]["components"][0]["parameters"][0]["text"] == "123456"
    button = seen["kwargs"]["json"]["template"]["components"][1]
    assert button["type"] == "button"
    assert button["sub_type"] == "url"
    assert button["parameters"][0]["text"] == "123456"
