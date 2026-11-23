"""Profile boundaries, identity linking and repair snapshots on disposable databases."""
import asyncio
import hashlib
import json
import os
import secrets
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi import FastAPI, Response, Request
from mongomock_motor import AsyncMongoMockClient
from motor.motor_asyncio import AsyncIOMotorClient

from auth_service import AuthService, AuthSettings, auth_router
from customer_profile import profile_router
from tests.test_google_oidc import callback

ADDRESS = dict(label='Home', line1='Test building', line2='', city='Test city', state='Test state', pin='123456', country='India')


def run(scenario, real=False):
    async def execute():
        client = AsyncIOMotorClient(os.getenv('MONGO_URL', 'mongodb://127.0.0.1:27017'), tz_aware=True, serverSelectionTimeoutMS=3000) if real else AsyncMongoMockClient(tz_aware=True)
        dbname = 'voltx_profile_test_' + secrets.token_hex(8)
        db = client[dbname]
        with patch.dict(os.environ, GOOGLE_CLIENT_ID='client', GOOGLE_CLIENT_SECRET='secret', GOOGLE_REDIRECT_URI='http://localhost:3000/api/auth/google/callback'):
            clock = [datetime.now(timezone.utc)]
            auth = AuthService(db, AuthSettings('test-only-profile-secret-with-at-least-32-characters', 'test', 'demo', True), clock=lambda: clock[0])
            try:
                await auth.initialize()
                app = FastAPI()
                app.include_router(auth_router(auth), prefix='/api')
                app.include_router(profile_router(lambda: auth), prefix='/api')
                import server
                app.include_router(server.api_router)
                app.middleware('http')(server.trusted_origin)
                with patch.object(server, 'auth_service', auth), patch.object(server, 'db', db):
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://localhost:3000', headers={'Origin': 'http://localhost:3000'}) as browser:
                        await scenario(auth, db, browser, clock)
            finally:
                assert dbname.startswith('voltx_profile_test_')
                await client.drop_database(dbname)
                if real:
                    client.close()
    asyncio.run(execute())


async def sign_in(auth, db, browser, uid='customer', phone='+919876543210', **fields):
    user = {'user_id': uid, 'role': 'customer', 'name': 'Test Customer', 'status': 'active', **fields}
    if phone:
        user.update(phone=phone, phone_verified_at=auth.clock().isoformat())
    await db.users.update_one({'user_id': uid}, {'$setOnInsert': user}, upsert=True)
    response = Response()
    await auth.login_response(user, response, Request({'type': 'http', 'headers': []}))
    cookie = response.headers['set-cookie'].split(';')[0].split('=', 1)[1]
    browser.cookies.set('access_token', cookie)
    return user


def test_profile_auth_allowlist_and_persistence():
    async def scenario(auth, db, browser, clock):
        assert (await browser.get('/api/customer/profile')).status_code == 401
        user = await sign_in(auth, db, browser)
        assert (await browser.post('/api/customer/addresses', json={**ADDRESS, 'revision': 0}, headers={'Origin': 'https://evil.example'})).status_code == 403
        for field in ('phone', 'email', 'role', 'user_id', 'auth_subject', 'phone_verified_at'):
            assert (await browser.patch('/api/customer/profile', json={'name': 'Test Name', field: 'evil'})).status_code == 422
        response = await browser.patch('/api/customer/profile', json={'name': ' Updated Customer '})
        assert response.json()['user']['name'] == 'Updated Customer'
        assert (await browser.get('/api/auth/me')).json()['name'] == 'Updated Customer'
        assert (await browser.patch('/api/customer/profile', json={'name': '  '})).status_code == 422
        await db.users.update_one({'user_id': user['user_id']}, {'$set': {'role': 'owner'}})
        assert (await browser.get('/api/customer/profile')).status_code == 403
    run(scenario)


def test_repair_physical_measurements_are_persisted_and_bounded():
    async def scenario(auth, db, browser, clock):
        await sign_in(auth, db, browser)
        response = await browser.post('/api/repairs', json={
            'charger_info': {'brand': 'Test', 'weight_kg': 8.5, 'length_cm': 42},
            'problem_description': 'Test repair',
        })
        assert response.status_code == 200
        assert response.json()['charger_info']['weight_kg'] == 8.5
        assert response.json()['charger_info']['length_cm'] == 42
        await db.chargers.insert_one({
            'charger_id': 'TEST-REGISTERED', 'owner_id': 'customer',
            'name': 'Registered charger', 'max_power_kw': 7.4,
        })
        registered = await browser.post('/api/repairs', json={
            'charger_id': 'TEST-REGISTERED',
            'charger_info': {'weight_kg': 9, 'length_cm': 45},
            'problem_description': 'Registered charger repair',
        })
        assert registered.status_code == 200
        assert registered.json()['charger_info']['power_rating'] == '7.4 kW'
        assert registered.json()['charger_info']['weight_kg'] == 9
        assert registered.json()['charger_info']['length_cm'] == 45
        assert (await browser.post('/api/repairs', json={
            'charger_info': {'brand': 'Test', 'weight_kg': 0, 'length_cm': 501},
            'problem_description': 'Invalid measurements',
        })).status_code == 422
    run(scenario)


def test_repair_retry_accepts_pre_measurement_fingerprint():
    async def scenario(auth, db, browser, clock):
        user = await sign_in(auth, db, browser)
        idempotency_key = 'legacy-measurement-retry'
        legacy_payload = {
            'customer_type': 'RETAIL',
            'charger_id': None,
            'charger_info': {
                'brand': 'Legacy', 'model': None, 'serial_number': None,
                'charger_type': None, 'power_rating': None,
            },
            'problem_description': 'Legacy retry',
            'reported_category': None,
            'photos': None,
            'whatsapp_opt_in': False,
        }
        creation_key = hashlib.sha256(json.dumps([user['user_id'], idempotency_key]).encode()).hexdigest()
        creation_fingerprint = hashlib.sha256(json.dumps(legacy_payload, sort_keys=True).encode()).hexdigest()
        await db.repair_requests.insert_one({
            'id': 'legacy-repair', 'repair_request_number': 'REP-LEGACY',
            'user_id': user['user_id'], 'status': 'REQUESTED',
            'charger_info': {'brand': 'Legacy'}, 'status_history': [],
            'creation_key': creation_key,
            'creation_fingerprint': creation_fingerprint,
        })
        response = await browser.post('/api/repairs', json={
            'idempotency_key': idempotency_key,
            'charger_info': {'brand': 'Legacy'},
            'problem_description': 'Legacy retry',
        })
        assert response.status_code == 200
        assert response.json()['id'] == 'legacy-repair'
        assert await db.repair_requests.count_documents({'creation_key': creation_key}) == 1
    run(scenario)


def test_address_crud_concurrency_and_defaults_real_mongo():
    async def scenario(auth, db, browser, clock):
        await sign_in(auth, db, browser)
        responses = await asyncio.gather(*[browser.post('/api/customer/addresses', json={**ADDRESS, 'revision': 0, 'default_pickup': True}) for _ in range(2)])
        assert sorted(r.status_code for r in responses) == [200, 409]
        profile = (await browser.get('/api/customer/profile')).json()
        aid = profile['addresses'][0]['id']
        assert profile['pickup_id'] == aid and profile['delivery_id'] is None
        original = browser.cookies.get('access_token')
        await sign_in(auth, db, browser, uid='foreign', phone='+919876543211')
        assert not (await browser.get('/api/customer/profile')).json()['addresses']
        assert (await browser.patch(f'/api/customer/addresses/{aid}', json={**ADDRESS, 'revision': 0})).status_code == 404
        assert (await browser.post('/api/repairs', json={'charger_info': {'brand': 'Test'}, 'problem_description': 'Test repair', 'pickup_address_id': aid})).status_code == 422
        browser.cookies.set('access_token', original)
        assert (await browser.patch('/api/customer/address-defaults', json={'revision': 1, 'pickup_id': 'foreign'})).status_code == 422
        assert (await browser.patch('/api/customer/addresses/foreign', json={**ADDRESS, 'revision': 1})).status_code == 404
        assert (await browser.request('DELETE', f'/api/customer/addresses/{aid}', json={'revision': 1})).status_code == 422
        assert (await browser.request('DELETE', f'/api/customer/addresses/{aid}', json={'revision': 1, 'pickup_id': aid, 'delivery_id': None})).status_code == 422
        assert (await browser.patch(f'/api/customer/addresses/{aid}', json={**ADDRESS, 'label': 'Office', 'revision': 1, 'default_delivery': True})).status_code == 200
        profile = (await browser.get('/api/customer/profile')).json()
        assert profile['delivery_id'] == aid and profile['pickup_id'] is None
        assert (await browser.request('DELETE', f'/api/customer/addresses/{aid}', json={'revision': 2, 'pickup_id': None, 'delivery_id': None})).status_code == 200
        assert not (await browser.get('/api/customer/profile')).json()['addresses']
    run(scenario, real=True)


def test_phone_link_session_policy_conflicts_and_purpose():
    async def scenario(auth, db, browser, clock):
        await sign_in(auth, db, browser)
        first = browser.cookies.get('access_token')
        await sign_in(auth, db, browser)
        second = browser.cookies.get('access_token')
        # Linking proof cannot be used by normal sign-in.
        response = await browser.post('/api/auth/link/phone/request', json={'phone': '9876543211'})
        cid = response.json()['challenge_id']
        proof = {'phone': '9876543211', 'challenge_id': cid, 'otp': '123456'}
        assert (await browser.post('/api/auth/verify-otp', json=proof)).status_code == 400
        browser.cookies.set('access_token', first)
        assert (await browser.post('/api/auth/link/phone/verify', json=proof)).status_code == 400
        browser.cookies.set('access_token', second)
        response = await browser.post('/api/auth/link/phone/verify', json=proof)
        assert response.status_code == 200, response.text
        assert response.json()['user']['phone'] == '+919876543211'
        assert (await browser.get('/api/auth/me')).status_code == 200
        browser.cookies.set('access_token', first)
        assert (await browser.get('/api/auth/me')).status_code == 401
        browser.cookies.set('access_token', second)
        assert (await browser.post('/api/auth/link/phone/verify', json=proof)).status_code == 400
        # A WhatsApp decision lease storage-fences concurrent phone replacement.
        await db.users.update_one({'user_id': 'customer'}, {'$set': {
            'whatsapp_decision_lease': {'owner': 'test-worker', 'until': clock[0] + timedelta(seconds=120)}}})
        cid = (await browser.post('/api/auth/link/phone/request', json={'phone': '9876543214'})).json()['challenge_id']
        blocked = await browser.post('/api/auth/link/phone/verify', json={
            'phone': '9876543214', 'challenge_id': cid, 'otp': '123456'})
        assert blocked.status_code == 409
        assert (await db.users.find_one({'user_id': 'customer'}))['phone'] == '+919876543211'
        await db.users.update_one({'user_id': 'customer'}, {'$unset': {'whatsapp_decision_lease': ''}})
        await db.users.insert_one({'user_id': 'other', 'phone': '+919876543212', 'role': 'customer'})
        cid = (await browser.post('/api/auth/link/phone/request', json={'phone': '9876543212'})).json()['challenge_id']
        assert (await browser.post('/api/auth/link/phone/verify', json={'phone': '9876543212', 'challenge_id': cid, 'otp': '123456'})).status_code == 409
        assert (await browser.get('/api/auth/me')).json()['phone'] == '+919876543211'
        clock[0] += timedelta(seconds=61)
        cid = (await browser.post('/api/auth/request-otp', json={'phone': '9876543211'})).json()['challenge_id']
        login = await browser.post('/api/auth/verify-otp', json={'phone': '9876543211', 'challenge_id': cid, 'otp': '123456'})
        assert login.json()['user']['user_id'] == 'customer'
        # Normal login proof cannot be used for linking.
        cid = (await browser.post('/api/auth/request-otp', json={'phone': '9876543213'})).json()['challenge_id']
        assert (await browser.post('/api/auth/link/phone/verify', json={'phone': '9876543213', 'challenge_id': cid, 'otp': '123456'})).status_code == 400
    run(scenario)


@pytest.mark.parametrize('kind', ['success', 'conflict', 'unverified', 'changed_session', 'cancelled'])
def test_google_link_purpose_and_identity(kind):
    async def scenario(auth, db, browser, clock):
        await sign_in(auth, db, browser)
        if kind == 'conflict':
            await db.users.insert_one({'user_id': 'other', 'auth_provider': 'google', 'auth_subject': 'subject', 'role': 'customer'})
        response = await browser.post('/api/auth/link/google/start')
        params = {k: v[0] for k, v in parse_qs(urlparse(response.json()['url']).query).items()}
        if kind == 'changed_session':
            await sign_in(auth, db, browser)
        if kind == 'cancelled':
            response = await browser.get('/api/auth/google/callback', params={'state': params['state'], 'error': 'access_denied'})
        else:
            response = await callback(auth, browser, params, overrides={'email_verified': kind != 'unverified'})
        expected = 'success' if kind == 'success' else 'conflict' if kind == 'conflict' else 'failed'
        assert response.headers['location'] == '/app/profile?google_link=' + expected
        assert (await browser.get('/api/auth/me')).json()['user_id'] == 'customer'
        customer = await db.users.find_one({'user_id': 'customer'})
        assert bool(customer.get('auth_subject')) == (kind == 'success')
        if kind == 'success':
            assert (await auth.google.user({'sub': 'subject', 'email': 'same@example.com', 'email_verified': True}))['user_id'] == 'customer'
        replay = await browser.get('/api/auth/google/callback', params={'state': params['state'], 'code': 'code'})
        assert 'google_error' in replay.headers['location']
    run(scenario)


def test_repair_snapshots_retry_and_redaction():
    async def scenario(auth, db, browser, clock):
        await sign_in(auth, db, browser)
        profile = (await browser.post('/api/customer/addresses', json={**ADDRESS, 'revision': 0, 'default_pickup': True})).json()
        aid = profile['addresses'][0]['id']
        body = {'idempotency_key': 'test-retry', 'charger_info': {'brand': 'Test'}, 'problem_description': 'Not charging', 'pickup_address_id': aid}
        assert (await browser.post('/api/repairs', json={**body, 'pickup_address': ADDRESS})).status_code == 422
        response = await browser.post('/api/repairs', json=body)
        assert response.status_code == 200, response.text
        repair = response.json()
        assert repair['pickup_address']['line1'] == ADDRESS['line1']
        await browser.request('DELETE', f'/api/customer/addresses/{aid}', json={'revision': 1, 'pickup_id': None, 'delivery_id': None})
        retry = await browser.post('/api/repairs', json=body)
        assert retry.json()['id'] == repair['id'] and retry.json()['pickup_address'] == repair['pickup_address']
        body['idempotency_key'] = 'new-retry'
        assert (await browser.post('/api/repairs', json=body)).status_code == 422
        import server
        sanitized = server.sanitize_repair({**repair, 'charger_id': 'test'}, {'user_id': 'unrelated-owner', 'role': 'owner'})
        assert 'pickup_address' not in sanitized
        assert await db.repair_requests.count_documents({}) == 1
    run(scenario)


def test_identity_race_real_mongo():
    async def scenario(auth, db, browser, clock):
        users, requests = [], []
        for uid, phone in [('one', '+919876543210'), ('two', '+919876543211')]:
            users.append(await sign_in(auth, db, browser, uid, phone))
            token = browser.cookies.get('access_token')
            requests.append(Request({'type': 'http', 'headers': [(b'cookie', ('access_token=' + token).encode())]}))
        async def connect(index):
            request, user = requests[index], users[index]
            try:
                await auth.google.link(request, {'user_id': user['user_id'], 'session_id': auth.session_id(request)}, {'sub': 'shared-subject', 'email': 'test@example.com', 'email_verified': True})
                return 200
            except Exception as error:
                return error.status_code
        assert sorted(await asyncio.gather(connect(0), connect(1))) == [200, 409]
        assert await db.users.count_documents({'auth_subject': 'shared-subject'}) == 1
        assert await db.users.count_documents({}) == 2
    run(scenario, real=True)


@pytest.mark.parametrize('case', ['wrong_code', 'expired', 'provider_failure'])
def test_phone_link_failures_preserve_identity(case):
    async def scenario(auth, db, browser, clock):
        await sign_in(auth, db, browser)
        if case == 'provider_failure':
            async def failed_send(*args):
                raise RuntimeError('Provider unavailable')
            auth.provider.send_otp = failed_send
        response = await browser.post('/api/auth/link/phone/request', json={'phone': '9876543211'})
        if case == 'provider_failure':
            assert response.status_code == 503
        else:
            if case == 'expired':
                clock[0] += timedelta(minutes=11)
            response = await browser.post('/api/auth/link/phone/verify', json={'phone': '9876543211', 'challenge_id': response.json()['challenge_id'], 'otp': '000000' if case == 'wrong_code' else '123456'})
            assert response.status_code == 400
        assert (await browser.get('/api/auth/me')).json()['phone'] == '+919876543210'
    run(scenario)


def test_google_customer_adds_phone_and_both_sign_ins_retain_dashboard_data():
    async def scenario(auth, db, browser, clock):
        await sign_in(auth, db, browser, phone=None, auth_provider='google', auth_subject='subject', google_verified_email='same@example.com')
        profile = (await browser.post('/api/customer/addresses', json={**ADDRESS, 'revision': 0})).json()
        aid = profile['addresses'][0]['id']
        repair = (await browser.post('/api/repairs', json={'charger_info': {'brand': 'Test'}, 'problem_description': 'Test repair', 'pickup_address_id': aid})).json()
        cid = (await browser.post('/api/auth/link/phone/request', json={'phone': '9876543210'})).json()['challenge_id']
        assert (await browser.post('/api/auth/link/phone/verify', json={'phone': '9876543210', 'challenge_id': cid, 'otp': '123456'})).status_code == 200
        await browser.post('/api/auth/logout')
        clock[0] += timedelta(seconds=61)
        cid = (await browser.post('/api/auth/request-otp', json={'phone': '9876543210'})).json()['challenge_id']
        response = await browser.post('/api/auth/verify-otp', json={'phone': '9876543210', 'challenge_id': cid, 'otp': '123456'})
        assert response.json()['user']['user_id'] == 'customer'
        assert (await browser.get('/api/customer/profile')).json()['addresses'][0]['id'] == aid
        assert (await browser.get('/api/repairs')).json()[0]['id'] == repair['id']
        await browser.post('/api/auth/logout')
        response = await browser.get('/api/auth/google/login')
        params = {k: v[0] for k, v in parse_qs(urlparse(response.headers['location']).query).items()}
        assert (await callback(auth, browser, params)).headers['location'] == '/login'
        assert (await browser.get('/api/auth/me')).json()['user_id'] == 'customer'
        assert (await browser.get('/api/customer/profile')).json()['addresses'][0]['id'] == aid
        assert (await browser.get('/api/repairs')).json()[0]['id'] == repair['id']
    run(scenario)


def test_phone_replacement_retention_is_single_document_and_survives_session_store_failure():
    async def scenario(auth, db, browser, clock):
        await sign_in(auth, db, browser)
        original = browser.cookies.get('access_token')
        await sign_in(auth, db, browser)
        initiating = browser.cookies.get('access_token')
        sid = auth.decode(initiating, 'session')['jti']
        for offset, number in enumerate(['9876543211', '9876543212']):
            cid = (await browser.post('/api/auth/link/phone/request', json={'phone': number})).json()['challenge_id']
            with patch.object(db.auth_sessions, 'update_one', side_effect=RuntimeError('Session store write unavailable')):
                response = await browser.post('/api/auth/link/phone/verify', json={'phone': number,'challenge_id':cid,'otp':'123456'})
            assert response.status_code == 200
            user = await db.users.find_one({'user_id':'customer'})
            assert user['phone'] == '+91'+number and user['auth_epoch'] == offset+1
            assert user['phone_generation'] == offset+1
            assert user['retained_session_id'] == sid
            assert (await browser.get('/api/auth/me')).status_code == 200
        await db.users.update_one({'user_id':'customer'}, {'$inc': {'auth_epoch':1}})
        assert (await browser.get('/api/auth/me')).status_code == 401
        browser.cookies.set('access_token',original)
        assert (await browser.get('/api/auth/me')).status_code == 401
        browser.cookies.set('access_token',initiating)
        await browser.post('/api/auth/logout')
        browser.cookies.set('access_token',initiating)
        assert (await browser.get('/api/auth/me')).status_code == 401
    run(scenario)
