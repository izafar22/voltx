"""Auth integration tests against an isolated, disposable MongoDB database.
Uses the configured Mongo server, never the application's DB_NAME.
"""
import asyncio
import os
import secrets
from contextlib import ExitStack
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from dotenv import dotenv_values
from fastapi import FastAPI, Request
from motor.motor_asyncio import AsyncIOMotorClient

from auth_service import AuthService, AuthSettings, auth_router, normalize_phone

SECRET = "test-only-secret-not-used-by-the-application-12345"
_runtime_loop = None
_runtime_client = None


@pytest.fixture(scope="module", autouse=True)
def mongo_runtime():
    global _runtime_loop, _runtime_client
    _runtime_loop = asyncio.new_event_loop()
    yield
    if _runtime_client is not None:
        _runtime_client.close()
    _runtime_loop.run_until_complete(_runtime_loop.shutdown_asyncgens())
    _runtime_loop.close()
    _runtime_client = None



def run(scenario):
    async def execute():
        global _runtime_client
        url = os.getenv('MONGO_URL') or dotenv_values(Path(__file__).parents[1] / '.env').get('MONGO_URL')
        if _runtime_client is None:
            _runtime_client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=15000, tz_aware=True)
        client = _runtime_client
        database_name = 'voltx_auth_test_' + secrets.token_hex(8)
        db = client[database_name]
        try:
            await client.admin.command('ping')
            clock = [datetime.now(timezone.utc)]
            service = AuthService(db, AuthSettings(SECRET, 'test', 'demo', True), clock=lambda: clock[0])
            await service.initialize()
            app = FastAPI()
            app.include_router(auth_router(service), prefix='/api')
            @app.get('/api/protected')
            async def protected(request: Request):
                return await service.authenticate(request)
            import server
            app.include_router(server.api_router)
            app.middleware('http')(server.trusted_origin)
            with ExitStack() as patches:
                patches.enter_context(patch.object(server, 'auth_service', service))
                patches.enter_context(patch.object(server, 'db', db))
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test', headers={'Origin': 'http://localhost:3000'}) as browser:
                    await scenario(service, db, browser, clock)
        finally:
            # Only this test's freshly generated database can be removed.
            assert database_name.startswith('voltx_auth_test_')
            await client.drop_database(database_name)
    _runtime_loop.run_until_complete(execute())


@pytest.mark.parametrize('phone', ['9876543210', '+919876543210', '91 98765 43210', '98765 43210', '(98765) 43210'])
def test_phone_normalization(phone):
    assert normalize_phone(phone) == '+919876543210'


@pytest.mark.parametrize('phone', ['123', '+15551234567', 'abcdefghij', '5876543210', '', '+91 98765abc43210'])
def test_invalid_phone(phone):
    with pytest.raises(Exception) as error:
        normalize_phone(phone)
    assert error.value.status_code == 422


async def challenge(browser, phone='9876543210'):
    response = await browser.post('/api/auth/request-otp', json={'phone': phone})
    assert response.status_code == 200
    return response.json()['challenge_id']


async def verify(browser, cid, phone='9876543210', otp='123456'):
    return await browser.post('/api/auth/verify-otp', json={'challenge_id': cid, 'phone': phone, 'otp': otp})


def test_new_customer_cookie_registration_wallet_and_logout():
    async def scenario(service, db, browser, clock):
        assert (await browser.get('/api/protected')).status_code == 401
        cid = await challenge(browser)
        doc = await db.auth_challenges.find_one({'_id': cid})
        assert doc['otp_hash'] != '123456' and 'otp' not in doc
        response = await verify(browser, cid)
        assert response.json()['registration_required']
        token = response.json()['registration_token']
        assert await db.users.count_documents({}) == 0
        browser.cookies.set('access_token', token)
        assert (await browser.get('/api/auth/me')).status_code == 401
        browser.cookies.clear()
        assert (await browser.post('/api/auth/register-customer', json={'name': 'New Customer'})).status_code == 401
        headers = {'Authorization': 'Bearer ' + token}
        assert (await browser.post('/api/auth/register-customer', headers=headers, json={'name': 'New Customer', 'role': 'admin'})).status_code == 422
        assert (await browser.post('/api/auth/register-customer', headers=headers, json={'name': '  '})).status_code == 422
        response = await browser.post('/api/auth/register-customer', headers=headers, json={'name': '  New Customer  ', 'email': 'hello@example.com'})
        assert response.status_code == 200
        assert 'token' not in response.json()
        assert 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=lax' in response.headers['set-cookie']
        user = response.json()['user']
        assert user['name'] == 'New Customer' and user['role'] == 'customer'
        assert await db.wallets.count_documents({'user_id': user['user_id']}) == 1
        assert (await db.wallets.find_one({'user_id': user['user_id']}))['balance'] == 0
        assert (await browser.get('/api/auth/me')).json() == user
        assert (await browser.post('/api/auth/register-customer', headers=headers, json={'name': 'Again'})).status_code == 401
        assert await db.users.count_documents({}) == 1
        old_cookie = browser.cookies.get('access_token')
        assert (await browser.post('/api/auth/logout')).status_code == 200
        browser.cookies.set('access_token', old_cookie)
        assert (await browser.get('/api/protected')).status_code == 401
        assert (await verify(browser, cid)).status_code == 400
    run(scenario)


def test_existing_roles_disabled_and_preserved_wallet():
    async def scenario(service, db, browser, clock):
        for index, role in enumerate(['customer', 'owner', 'admin']):
            phone = f'+91900000000{index + 1}'
            await db.users.insert_one({'user_id': role, 'phone': phone, 'name': 'Existing', 'role': role})
            await db.wallets.insert_one({'user_id': role, 'balance': 250})
            cid = await challenge(browser, phone)
            response = await verify(browser, cid, phone)
            assert response.json()['user']['role'] == role and not response.json()['registration_required']
            assert (await db.wallets.find_one({'user_id': role}))['balance'] == 250
        await db.users.update_one({'user_id': 'admin'}, {'$set': {'status': 'disabled'}})
        assert (await browser.get('/api/auth/me')).status_code == 403
        clock[0] += timedelta(seconds=61)
        cid = await challenge(browser, '+919000000003')
        assert (await verify(browser, cid, '+919000000003')).status_code == 403
    run(scenario)


def test_wrong_expired_attempt_limits_and_cooldown():
    async def scenario(service, db, browser, clock):
        assert (await browser.post('/api/auth/request-otp', json={'phone': 'bad'})).status_code == 422
        cid = await challenge(browser)
        assert (await browser.post('/api/auth/request-otp', json={'phone': '+919876543210'})).status_code == 429
        for attempt in range(5):
            response = await verify(browser, cid, otp='000000')
            assert response.status_code == (429 if attempt == 4 else 400)
        assert (await verify(browser, cid)).status_code == 429
        clock[0] += timedelta(seconds=61)
        cid = await challenge(browser)
        clock[0] += timedelta(minutes=11)
        assert (await verify(browser, cid)).status_code == 400
        assert await db.users.count_documents({}) == 0
    run(scenario)


def test_concurrent_registration_creates_one_account_and_wallet():
    async def scenario(service, db, browser, clock):
        token = (await verify(browser, await challenge(browser))).json()['registration_token']
        responses = await asyncio.gather(*[browser.post('/api/auth/register-customer', headers={'Authorization': 'Bearer '+token}, json={'name': 'Parallel Customer'}) for _ in range(2)])
        assert sorted(r.status_code for r in responses) in ([200, 409], [200, 401])
        assert await db.users.count_documents({}) == 1
        assert await db.wallets.count_documents({}) == 1
    run(scenario)


def test_provider_fail_closed_and_no_otp_exposure():
    async def scenario(service, db, browser, clock):
        from fastapi import HTTPException
        settings = AuthSettings(SECRET, 'production', 'provider', False, ('https://voltx.example',))
        unconfigured = AuthService(db, settings)
        with pytest.raises(HTTPException) as failure:
            await unconfigured.request_otp('9876543210', 'test')
        assert failure.value.status_code == 503
        class CaptureProvider:
            code = None
            async def send_otp(self, phone, code): self.code = code
        provider = CaptureProvider()
        production = AuthService(db, settings, provider)
        result = await production.request_otp('9876543210', 'test')
        assert 'demo_otp' not in result and len(provider.code) == 6 and provider.code.isdigit()
        assert (await db.auth_challenges.find_one({'_id': result['challenge_id']}))['otp_hash'] != provider.code
        silent_demo = AuthService(db, AuthSettings(SECRET, 'test', 'demo', False))
        assert 'demo_otp' not in await silent_demo.request_otp('9876543211', 'test')
    run(scenario)


def test_safe_migration_and_index_uniqueness():
    async def scenario(service, db, browser, clock):
        await db.users.insert_one({'user_id': 'legacy', 'phone': '98765 43210', 'role': 'customer', 'name': 'Legacy'})
        await service.initialize()
        assert (await db.users.find_one({'user_id': 'legacy'}))['phone'] == '+919876543210'
        assert (await db.users.index_information())['auth_phone_partial_unique']['unique']
        await db.users.insert_one({'user_id': 'collision', 'phone': '91 9876543210'})
        with pytest.raises(RuntimeError, match='collision'):
            await service.initialize()
        assert (await db.users.find_one({'user_id': 'collision'}))['phone'] == '91 9876543210'
    run(scenario)


def test_actual_protected_routes_origin_and_customer_roles():
    async def scenario(service, db, browser, clock):
        assert (await browser.get('/api/wallet')).status_code == 401
        assert (await browser.post('/api/auth/request-otp', headers={'Origin':'https://evil.example'}, json={'phone':'9876543210'})).status_code == 403
        token = (await verify(browser, await challenge(browser))).json()['registration_token']
        assert (await browser.post('/api/auth/register-customer', headers={'Authorization':'Bearer '+token}, json={'name':'Customer'})).status_code == 200
        assert (await browser.get('/api/wallet')).json()['balance'] == 0
        assert (await browser.get('/api/sessions')).json() == []
        assert (await browser.get('/api/repairs')).json() == []
        assert (await browser.get('/api/admin/summary')).status_code == 403
        assert (await browser.get('/api/owner/summary')).status_code == 403
        browser.headers.pop('Origin')
        assert (await browser.post('/api/auth/logout')).status_code == 403
    run(scenario)


def test_expired_registration_grant_and_production_cookie():
    async def scenario(service, db, browser, clock):
        import jwt
        from fastapi import HTTPException, Response
        from starlette.requests import Request
        expired = jwt.encode({'sub': '+919876543210', 'jti':'expired', 'purpose':'registration', 'exp': datetime.now(timezone.utc)-timedelta(seconds=1)}, SECRET, algorithm='HS256')
        with pytest.raises(HTTPException) as error:
            await service.register(expired, 'Customer', '')
        assert error.value.status_code == 401
        production = AuthService(db, AuthSettings(SECRET,'production','provider',False,('https://voltx.example',)))
        response = Response()
        await production.login_response({'user_id':'test','role':'customer'},response,Request({'type':'http','headers':[]}))
        assert 'Secure' in response.headers['set-cookie'] and 'HttpOnly' in response.headers['set-cookie']
    run(scenario)


def test_legacy_full_phone_index_migrates_without_data_loss():
    async def scenario(service, db, browser, clock):
        await db.users.drop_index('auth_phone_partial_unique')
        await db.users.create_index('phone', unique=True, name='phone_1')
        await db.users.insert_one({'user_id': 'legacy', 'phone': '+919876543210'})
        await service.initialize()
        await db.users.insert_many([{'user_id': 'google1'}, {'user_id': 'google2'}, {'user_id': 'null1', 'phone': None}, {'user_id': 'null2', 'phone': None}])
        from pymongo.errors import DuplicateKeyError
        with pytest.raises(DuplicateKeyError):
            await db.users.insert_one({'user_id': 'duplicate', 'phone': '+919876543210'})
        assert await db.users.count_documents({}) == 5
        await service.initialize()
        assert await db.users.count_documents({}) == 5
    run(scenario)


@pytest.mark.parametrize('legacy_index', ['phone_1', 'auth_phone_unique'])
def test_representative_legacy_phone_migration_preserves_customer_history(legacy_index):
    async def scenario(service, db, browser, clock):
        from pymongo.errors import DuplicateKeyError
        await db.users.drop_index('auth_phone_partial_unique')
        await db.users.create_index('phone', unique=True, name=legacy_index)
        existing = [
            {'user_id': 'sms_customer', 'phone': '98765 43210', 'role': 'customer', 'name': 'Existing Customer', 'email': 'same@example.com'},
            {'user_id': 'owner', 'phone': '+919000000002', 'role': 'owner', 'name': 'Existing Owner'},
            {'user_id': 'admin', 'phone': '+919000000001', 'role': 'admin', 'name': 'Existing Admin'},
            {'user_id': 'legacy_invalid', 'phone': 'legacy-invalid', 'role': 'customer'},
            {'user_id': 'legacy_missing', 'role': 'customer'},
        ]
        await db.users.insert_many(existing)
        await db.wallets.insert_many([{'user_id': u['user_id'], 'balance': 125.5} for u in existing])
        await db.repairs.insert_one({'id': 'existing_repair', 'user_id': 'sms_customer', 'status': 'RECEIVED_AT_VOLTX', 'estimate': {'total': 1250}})
        before_users = {u['user_id']: u async for u in db.users.find({})}
        before_wallets = [w async for w in db.wallets.find({})]
        before_repairs = [r async for r in db.repairs.find({})]
        await service.initialize()
        indexes = await db.users.index_information()
        assert legacy_index not in indexes
        assert indexes['auth_phone_partial_unique']['partialFilterExpression'] == {'phone': {'$type': 'string'}}
        for uid, original in before_users.items():
            expected = {**original, 'phone': '+919876543210'} if uid == 'sms_customer' else original
            assert await db.users.find_one({'user_id': uid}) == expected
        assert [w async for w in db.wallets.find({})] == before_wallets
        assert [r async for r in db.repairs.find({})] == before_repairs
        # SMS still signs into the original customer and retains the existing balance.
        response = await verify(browser, await challenge(browser))
        assert response.json()['user']['user_id'] == 'sms_customer'
        assert (await db.wallets.find_one({'user_id': 'sms_customer'}))['balance'] == 125.5
        google = await service.google.user({'sub': 'new-google', 'email': 'same@example.com', 'email_verified': True})
        assert google['user_id'] != 'sms_customer' and google['role'] == 'customer'
        await service.google.user({'sub': 'another-google'})
        await db.users.insert_many([{'user_id': 'null1', 'phone': None}, {'user_id': 'null2', 'phone': None}])
        with pytest.raises(DuplicateKeyError):
            await db.users.insert_one({'user_id': 'duplicate_phone', 'phone': '+919876543210'})
        with pytest.raises(DuplicateKeyError):
            await db.users.insert_one({'user_id': 'duplicate_google', 'auth_provider': 'google', 'auth_subject': 'new-google'})
        await service.initialize()  # Repeated startup is safe with phone-less users present.
        assert await db.users.count_documents({}) == 9
        assert await db.repairs.count_documents({}) == 1
    run(scenario)


def test_legacy_normalization_collision_leaves_records_and_index_untouched():
    async def scenario(service, db, browser, clock):
        await db.users.drop_index('auth_phone_partial_unique')
        await db.users.create_index('phone', unique=True, name='phone_1')
        await db.users.insert_many([{'user_id': 'a', 'phone': '98765 43210'}, {'user_id': 'b', 'phone': '+919876543210'}])
        before = [u async for u in db.users.find({})]
        with pytest.raises(RuntimeError, match='collision'):
            await service.initialize()
        assert [u async for u in db.users.find({})] == before
        indexes = await db.users.index_information()
        assert indexes['phone_1']['unique'] and 'auth_phone_partial_unique' not in indexes
    run(scenario)
