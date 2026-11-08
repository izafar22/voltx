"""Offline code/JWKS tests; all provider traffic is mocked."""
import asyncio
import base64
import hashlib
import json
import time
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from mongomock_motor import AsyncMongoMockClient
from auth_service import AuthService, AuthSettings, auth_router

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
JWK = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key()))
JWK['kid'] = 'test-key'


def run(scenario, production=False):
    async def execute():
        with patch.dict('os.environ', GOOGLE_CLIENT_ID='client', GOOGLE_CLIENT_SECRET='secret',
                        GOOGLE_REDIRECT_URI=('https://evchargerrepair.in' if production else 'http://localhost:3000') + '/api/auth/google/callback'):
            service = AuthService(AsyncMongoMockClient(tz_aware=True).db,
                                  AuthSettings('test-only-secret-with-thirty-two-characters', 'production' if production else 'test', 'provider' if production else 'demo', not production, ('https://evchargerrepair.in',) if production else ('http://localhost:3000',)))
            await service.initialize()
            app = FastAPI()
            app.include_router(auth_router(service), prefix='/api')
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='https://evchargerrepair.in' if production else 'http://localhost:3000') as browser:
                await scenario(service, browser)
    asyncio.run(execute())


async def start(service, browser):
    response = await browser.get('/api/auth/google/login')
    assert response.status_code == 303
    params = {k: v[0] for k, v in parse_qs(urlparse(response.headers['location']).query).items()}
    transaction = await service.db.auth_google_transactions.find_one({'_id': service.digest(params['state'])})
    assert params['scope'] == 'openid email profile'
    assert params['code_challenge_method'] == 'S256'
    assert params['code_challenge'] == base64.urlsafe_b64encode(hashlib.sha256(transaction['verifier'].encode()).digest()).rstrip(b'=').decode()
    assert transaction['nonce'] == params['nonce']
    assert transaction['binding'] != browser.cookies.get('google_transaction')
    return params


def provider(params, overrides=None, wrong_key=False, exchange_error=False):
    claims = {'iss': 'https://accounts.google.com', 'aud': 'client', 'sub': 'subject',
              'iat': int(time.time()), 'exp': int(time.time()) + 300, 'nonce': params['nonce'],
              'name': 'Customer', 'email': 'same@example.com', 'email_verified': True}
    claims.update(overrides or {})
    token = jwt.encode(claims, rsa.generate_private_key(public_exponent=65537, key_size=2048) if wrong_key else KEY,
                       algorithm='RS256', headers={'kid': 'test-key'})
    async def post(self, url, **kwargs):
        assert kwargs['data']['code_verifier']
        return httpx.Response(400 if exchange_error else 200, json={'id_token': token}, request=httpx.Request('POST', url))
    async def get(self, url, **kwargs):
        return httpx.Response(200, json={'keys': [JWK]}, request=httpx.Request('GET', url))
    return patch.object(httpx.AsyncClient, 'post', post), patch.object(httpx.AsyncClient, 'get', get)


async def callback(service, browser, params, **kwargs):
    # Patch provider calls only; browser ASGI requests use send directly.
    p, g = provider(params, **kwargs)
    with p, g:
        return await browser.request('GET', '/api/auth/google/callback', params={'state': params['state'], 'code': 'code'})


def test_existing_email_requires_explicit_linking():
    async def scenario(service, browser):
        await service.db.users.insert_one({'user_id': 'admin', 'phone': '+919876543210', 'email': 'same@example.com', 'role': 'admin', 'status': 'active'})
        params = await start(service, browser)
        response = await callback(service, browser, params)
        assert response.headers['location'] == '/login?google_error=link_required'
        assert await service.db.users.count_documents({}) == 1
        assert (await browser.get('/api/auth/me')).status_code == 401
    run(scenario)


def test_new_google_user_is_customer():
    async def scenario(service, browser):
        params = await start(service, browser)
        response = await callback(service, browser, params)
        assert response.headers['location'] == '/login'
        assert (await browser.get('/api/auth/me')).json()['role'] == 'customer'
    run(scenario)


def test_authenticated_admin_can_link_and_sign_in():
    async def scenario(service, browser):
        await service.db.users.insert_one({'user_id': 'admin', 'phone': '+919876543210', 'email': 'same@example.com', 'role': 'admin', 'status': 'active'})
        admin = await service.db.users.find_one({'user_id': 'admin'})
        from fastapi import Response
        from starlette.requests import Request
        response = Response()
        await service.login_response(admin, response, Request({'type': 'http', 'headers': [], 'method': 'GET', 'path': '/', 'query_string': b'', 'client': ('127.0.0.1', 1)}))
        from http.cookies import SimpleCookie
        cookies = SimpleCookie()
        cookies.load(response.headers['set-cookie'])
        browser.cookies.set('access_token', cookies['access_token'].value)
        link = await browser.get('/api/auth/google/link')
        assert link.status_code == 303
        params = {k: v[0] for k, v in parse_qs(urlparse(link.headers['location']).query).items()}
        linked = await callback(service, browser, params)
        assert linked.headers['location'] == '/admin'
        assert (await service.db.users.find_one({'user_id': 'admin'}))['auth_subject'] == 'subject'
        await browser.post('/api/auth/logout')
        params = await start(service, browser)
        signed_in = await callback(service, browser, params)
        assert signed_in.headers['location'] == '/login'
        assert (await browser.get('/api/auth/me')).json()['role'] == 'admin'
    run(scenario)


@pytest.mark.parametrize('overrides,wrong_key', [({'iss': 'evil'}, False), ({'aud': 'other'}, False),
    ({'nonce': 'wrong'}, False), ({'exp': 1}, False), ({'sub': ''}, False), ({'azp': 'evil'}, False), ({'aud': ['client', 'other']}, False), ({}, True)])
def test_invalid_tokens(overrides, wrong_key):
    async def scenario(service, browser):
        params = await start(service, browser)
        response = await callback(service, browser, params, overrides=overrides, wrong_key=wrong_key)
        assert response.headers['location'].endswith('google_error=1')
        assert await service.db.auth_sessions.count_documents({}) == 0
    run(scenario)


@pytest.mark.parametrize('case', ['expired', 'binding', 'malformed', 'denial', 'exchange'])
def test_failed_transactions(case):
    async def scenario(service, browser):
        params = await start(service, browser)
        if case == 'expired':
            await service.db.auth_google_transactions.update_many({}, {'$set': {'expires_at': service.clock()-timedelta(seconds=1)}})
        if case == 'binding':
            browser.cookies.clear()
        if case == 'malformed':
            params['state'] = 'bad'
        if case == 'denial':
            response = await browser.get('/api/auth/google/callback', params={'state': params['state'], 'error': 'access_denied'})
        else:
            response = await callback(service, browser, params, exchange_error=case == 'exchange')
        assert response.headers['location'].endswith('google_error=1')
        assert await service.db.users.count_documents({}) == 0
    run(scenario)


def test_atomic_callback_replay_and_key_rotation():
    async def scenario(service, browser):
        params = await start(service, browser)
        service.google.keys = [{**JWK, 'kid': 'old'}]
        service.google.keys_until = time.monotonic() + 100
        responses = await asyncio.gather(callback(service, browser, params), callback(service, browser, params))
        assert sorted(r.headers['location'] for r in responses) == ['/login', '/login?google_error=1']
        assert await service.db.auth_sessions.count_documents({}) == 1
        assert (await callback(service, browser, params)).headers['location'].endswith('google_error=1')
    run(scenario)


def test_duplicate_identity_and_role_guard():
    async def scenario(service, browser):
        users = await asyncio.gather(*[service.google.user({'sub': 'subject'}) for _ in range(2)])
        assert users[0]['user_id'] == users[1]['user_id']
        await service.db.users.update_many({}, {'$set': {'role': 'admin'}})
        assert (await service.google.user({'sub': 'subject'}))['role'] == 'admin'
    run(scenario)



@pytest.mark.parametrize('role,status', [('unknown', 'active'), ('customer', 'suspended')])
def test_existing_google_identity_rejects_invalid_account(role, status):
    async def scenario(service, browser):
        await service.db.users.insert_one({
            'user_id': 'existing', 'auth_provider': 'google', 'auth_subject': 'subject',
            'role': role, 'status': status
        })
        params = await start(service, browser)
        response = await callback(service, browser, params)
        assert response.headers['location'] == '/login?google_error=1'
        assert await service.db.auth_sessions.count_documents({}) == 0
    run(scenario)


def test_unconfigured_google_preserves_sms_and_fixed_destination():
    async def scenario(service, browser):
        service.google.client_secret = ''
        assert (await browser.get('/api/auth/google/login')).status_code == 503
        assert (await browser.post('/api/auth/request-otp', json={'phone': '9876543210'})).status_code == 200
        service.google.client_secret = 'secret'
        response = await browser.get('/api/auth/google/login?return_to=https://evil.example')
        params = parse_qs(urlparse(response.headers['location']).query)
        assert params['redirect_uri'] == ['http://localhost:3000/api/auth/google/callback']
        assert 'return_to' not in params
    run(scenario)


def test_production_same_origin_cookie_round_trip_rotation_and_logout():
    from http.cookies import SimpleCookie
    async def scenario(service, browser):
        params = await start(service, browser)
        assert params['redirect_uri'] == 'https://evchargerrepair.in/api/auth/google/callback'
        binding = next(cookie for cookie in browser.cookies.jar if cookie.name == 'google_transaction')
        assert binding.secure and binding.path == '/api/auth/google' and not binding.domain_specified
        response = await callback(service, browser, params)
        assert response.headers['location'] == '/login'
        assert response.headers['cache-control'] == 'no-store'
        assert response.headers['referrer-policy'] == 'no-referrer'
        cookies = SimpleCookie()
        for value in response.headers.get_list('set-cookie'):
            cookies.load(value)
        session = cookies['access_token']
        assert session['secure'] and session['httponly'] and session['samesite'] == 'lax'
        assert session['path'] == '/' and not session['domain']
        assert cookies['google_transaction']['max-age'] == '0'
        assert not browser.cookies.get('google_transaction')
        assert (await browser.get('/api/auth/me')).json()['role'] == 'customer'
        old_token = browser.cookies.get('access_token')
        # Cookie jar refuses to send Secure cookies over HTTP.
        assert (await browser.get('http://evchargerrepair.in/api/auth/me')).status_code == 401
        assert (await callback(service, browser, await start(service, browser))).headers['location'] == '/login'
        assert await service.db.auth_sessions.count_documents({}) == 1
        assert (await browser.get('/api/auth/me', headers={'Cookie': 'access_token=' + old_token})).status_code == 401
        current_token = browser.cookies.get('access_token')
        assert (await browser.post('/api/auth/logout')).status_code == 200
        assert (await browser.get('/api/auth/me', headers={'Cookie': 'access_token=' + current_token})).status_code == 401
    run(scenario, production=True)
