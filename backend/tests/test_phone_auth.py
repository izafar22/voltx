"""Offline SMS delivery and phone-identity tests; never send a real SMS."""
import asyncio
import json
import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from mongomock_motor import AsyncMongoMockClient

from auth_service import AuthService, AuthSettings, auth_router, safe_user, UnconfiguredOtpProvider
from sms_provider import Msg91OtpProvider, Msg91Settings, SmsDeliveryError
from services.whatsapp_service import consent_record

SETTINGS = Msg91Settings('test-provider-key', 'test-template', 'RUSHXX', 'otp')
SECRET = 'test-only-phone-auth-secret-longer-than-thirty-two'
PHONE = '+919876543210'


def run(test):
    async def scenario():
        now = [datetime.now(timezone.utc)]
        service = AuthService(AsyncMongoMockClient(tz_aware=True).db, AuthSettings(SECRET, 'test', 'demo', True), clock=lambda: now[0])
        await service.initialize()
        app = FastAPI(); app.include_router(auth_router(service), prefix='/api')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
            await test(service, client, now)
    asyncio.run(scenario())


def test_msg91_delivery_contract_redaction_and_factory(caplog):
    async def scenario():
        def handler(request):
            assert str(request.url) == 'https://control.msg91.com/api/v5/flow'
            assert request.headers['authkey'] == SETTINGS.auth_key
            assert json.loads(request.content) == {'template_id': 'test-template', 'short_url': '0', 'recipients': [{'mobiles': PHONE[1:], 'otp': '654321'}]}
            assert request.extensions['timeout'] == {'connect': 3, 'read': 10, 'write': 5, 'pool': 3}
            return httpx.Response(200, json={'type': 'success', 'message': 'request-id'})
        await Msg91OtpProvider(SETTINGS, httpx.MockTransport(handler)).send_otp(PHONE, '654321')
    with caplog.at_level(logging.DEBUG): asyncio.run(scenario())
    assert SETTINGS.auth_key not in caplog.text and '654321' not in caplog.text and PHONE not in caplog.text
    assert SETTINGS.auth_key not in repr(SETTINGS)
    with patch.dict('os.environ', SMS_PROVIDER='msg91', MSG91_AUTH_KEY=SETTINGS.auth_key, MSG91_TEMPLATE_ID=SETTINGS.template_id, MSG91_SENDER_ID=SETTINGS.sender_id, MSG91_OTP_VARIABLE='otp'):
        service = AuthService(None, AuthSettings(SECRET,'test','provider'))
        assert isinstance(service.provider, Msg91OtpProvider)
        with patch.dict('os.environ', MSG91_OTP_VARIABLE='mobiles'):
            assert isinstance(AuthService(None, service.settings).provider, UnconfiguredOtpProvider)


@pytest.mark.parametrize('status,body', [(401, {'type':'error','message':'provider-secret'}), (429,{}), (500,{}), (302,{}), (200,{'type':'error','message':'rejected'}), (200,{}), (200,{'type':'success','message':''}), (200,[]), (200,None)])
def test_delivery_rejections_are_not_success(status, body):
    async def scenario():
        transport=httpx.MockTransport(lambda request: httpx.Response(status, json=body))
        with pytest.raises(SmsDeliveryError, match='SMS delivery unavailable'):
            await Msg91OtpProvider(SETTINGS, transport).send_otp(PHONE, '654321')
    asyncio.run(scenario())


@pytest.mark.parametrize('error', [httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError])
def test_delivery_network_errors_do_not_leak_or_retry(error):
    async def scenario():
        calls=[]
        def handler(request):
            calls.append(True); raise error('secret-key and code must not escape', request=request)
        with pytest.raises(SmsDeliveryError) as result:
            await Msg91OtpProvider(SETTINGS, httpx.MockTransport(handler)).send_otp(PHONE, '654321')
        assert str(result.value) == 'SMS delivery unavailable' and len(calls)==1
    asyncio.run(scenario())


def test_provider_failure_consumes_undelivered_challenge():
    async def scenario(service, client, now):
        class Reject:
            async def send_otp(self, phone, code): raise SmsDeliveryError('private provider diagnostic')
        service.provider=Reject()
        response=await client.post('/api/auth/request-otp',json={'phone':PHONE})
        assert response.status_code==503 and 'private' not in response.text
        record=await service.db.auth_challenges.find_one({})
        assert record['consumed'] and not record['delivered'] and 'otp' not in record
        with pytest.raises(HTTPException): await service.verify(record['_id'],PHONE,'123456')
    run(scenario)


async def google_user(service, client, subject='subject'):
    user=await service.google.user({'sub':subject})
    from fastapi import Response
    from starlette.requests import Request
    response=Response()
    await service.login_response(user,response,Request({'type':'http','headers':[]}))
    token=response.headers['set-cookie'].split('access_token=',1)[1].split(';',1)[0]
    client.cookies.set('access_token',token)
    return user, token


async def link_request(client, phone=PHONE):
    r=await client.post('/api/auth/phone/request-otp',json={'phone':phone})
    assert r.status_code==200,r.text
    return r.json()['challenge_id']


async def link_verify(client, cid, phone=PHONE, otp='123456'):
    return await client.post('/api/auth/phone/verify-otp',json={'phone':phone,'challenge_id':cid,'otp':otp})


def test_google_link_preserves_identity_history_session_and_explicit_consent():
    async def scenario(service,client,now):
        user,token=await google_user(service,client)
        await service.db.repairs.insert_one({'id':'existing','user_id':user['user_id']})
        before_wallet=await service.db.wallets.find_one({'user_id':user['user_id']})
        assert not (await client.get('/api/auth/me')).json()['phone_verified']
        with pytest.raises(HTTPException): consent_record(True,user,'now')
        response=await link_verify(client,await link_request(client))
        assert response.status_code==200,response.text
        profile=response.json()['user']
        assert profile['user_id']==user['user_id'] and profile['phone']==PHONE and profile['phone_verified']
        assert client.cookies.get('access_token')==token
        assert (await client.get('/api/auth/me')).json()==profile
        assert await service.db.users.count_documents({})==1
        assert await service.db.wallets.find_one({'user_id':user['user_id']})==before_wallet
        assert (await service.db.repairs.find_one({'id':'existing'}))['user_id']==user['user_id']
        assert not (await service.db.repairs.find_one({'id':'existing'})).get('whatsapp_consent')
        linked=await service.db.users.find_one({'user_id':user['user_id']})
        assert consent_record(False,linked,'now')=={'opted_in':False}
        assert consent_record(True,linked,'now')['destination']==PHONE
        assert (await client.post('/api/auth/phone/request-otp',json={'phone':'+919876543211'})).status_code==409
    run(scenario)


def test_link_challenge_cannot_log_in_or_link_a_different_user():
    async def scenario(service,client,now):
        first,_=await google_user(service,client,'first')
        cid=await link_request(client)
        assert (await client.post('/api/auth/verify-otp',json={'phone':PHONE,'challenge_id':cid,'otp':'123456'})).status_code==400
        await google_user(service,client,'second')
        assert (await link_verify(client,cid)).status_code==400
        assert not (await service.db.auth_challenges.find_one({'_id':cid}))['consumed']
        assert not (await service.db.users.find_one({'user_id':first['user_id']})).get('phone')
        client.cookies.clear()
        assert (await link_verify(client,cid)).status_code==401
    run(scenario)


def test_duplicate_phone_does_not_merge_accounts_or_move_repairs():
    async def scenario(service,client,now):
        await service.db.users.insert_one({'user_id':'original','phone':PHONE,'role':'customer','phone_verified_at':'earlier'})
        user,_=await google_user(service,client)
        cid=await link_request(client)
        response=await link_verify(client,cid)
        assert response.status_code==409 and 'account recovery' in response.text
        assert not (await service.db.users.find_one({'user_id':user['user_id']})).get('phone')
        assert (await service.db.users.find_one({'phone':PHONE}))['user_id']=='original'
        assert (await link_verify(client,cid)).status_code==400
    run(scenario)


def test_concurrent_links_single_winner_and_shared_limits():
    async def scenario(service,client,now):
        user,_=await google_user(service,client)
        cid=await link_request(client)
        responses=await asyncio.gather(link_verify(client,cid),link_verify(client,cid))
        assert sorted(r.status_code for r in responses) in ([200,400],[200,409])
        assert await service.db.users.count_documents({'phone':PHONE})==1
        await google_user(service,client,'another')
        assert (await client.post('/api/auth/phone/request-otp',json={'phone':PHONE})).status_code==429
        # A phone-less account cannot acquire a privileged role through linking.
        await service.db.users.update_one({'user_id':user['user_id']},{'$set':{'role':'admin'}})
        assert (await client.post('/api/auth/verify-otp',json={'phone':PHONE,'challenge_id':cid,'otp':'123456'})).status_code==400
    run(scenario)


def test_link_wrong_attempts_expiry_and_login_challenge_isolation():
    async def scenario(service,client,now):
        await google_user(service,client)
        cid=await link_request(client)
        for i in range(5):
            assert (await link_verify(client,cid,otp='000000')).status_code==(429 if i==4 else 400)
        now[0]+=timedelta(seconds=61)
        cid=await link_request(client)
        now[0]+=timedelta(minutes=6)
        assert (await link_verify(client,cid)).status_code==400
        now[0]+=timedelta(seconds=61)
        r=await client.post('/api/auth/request-otp',json={'phone':PHONE})
        assert (await link_verify(client,r.json()['challenge_id'])).status_code==400
    run(scenario)


def test_concurrent_login_verification_single_use_and_verified_profile():
    async def scenario(service,client,now):
        await service.db.users.insert_one({'user_id':'existing','phone':PHONE,'role':'customer'})
        cid=(await client.post('/api/auth/request-otp',json={'phone':PHONE})).json()['challenge_id']
        async def verify():
            return await client.post('/api/auth/verify-otp',json={'phone':PHONE,'challenge_id':cid,'otp':'123456'})
        responses=await asyncio.gather(verify(),verify())
        assert sorted(r.status_code for r in responses)==[200,400]
        assert (await client.get('/api/auth/me')).json()['phone_verified']
    run(scenario)


def test_limits_are_shared_by_multiple_service_instances():
    async def scenario(service,client,now):
        other=AuthService(service.db,service.settings,clock=service.clock)
        await service.limit('shared-ip',2,3600)
        await other.limit('shared-ip',2,3600)
        with pytest.raises(HTTPException) as result: await service.limit('shared-ip',2,3600)
        assert result.value.status_code==429
    run(scenario)


def test_legacy_customer_can_verify_only_assigned_phone_and_roles_are_protected():
    async def scenario(service,client,now):
        user={'user_id':'legacy','role':'customer','phone':PHONE}
        await service.db.users.insert_one(user)
        with pytest.raises(HTTPException) as blocked: await service.request_phone_link(user,'+919876543211','test')
        assert blocked.value.status_code==403
        issued=await service.request_phone_link(user,PHONE,'test')
        profile=await service.verify_phone_link(user,issued['challenge_id'],PHONE,'123456')
        assert profile['user_id']=='legacy' and profile['phone_verified']
        for role in ['owner','admin']:
            with pytest.raises(HTTPException) as error: await service.request_phone_link({**user,'role':role},PHONE,'test')
            assert error.value.status_code==403
    run(scenario)


def test_disabled_account_cannot_complete_an_inflight_phone_link():
    async def scenario(service,client,now):
        user,_=await google_user(service,client)
        issued=await service.request_phone_link(user,PHONE,'test')
        await service.db.users.update_one({'user_id':user['user_id']},{'$set':{'status':'disabled'}})
        with pytest.raises(HTTPException) as error:
            await service.verify_phone_link(user,issued['challenge_id'],PHONE,'123456')
        assert error.value.status_code==409
        assert not (await service.db.users.find_one({'user_id':user['user_id']})).get('phone')
    run(scenario)
