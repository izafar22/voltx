"""Google code flow. Provider URLs and the post-login destination are never browser supplied."""
import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from datetime import timedelta
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from pymongo.errors import DuplicateKeyError

AUTHORIZE = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN = 'https://oauth2.googleapis.com/token'
JWKS = 'https://www.googleapis.com/oauth2/v3/certs'
COOKIE = 'google_transaction'


class ExistingAccountLinkRequired(ValueError):
    pass


class GoogleOIDC:
    def __init__(self, auth):
        self.auth = auth
        self.client_id = os.getenv('GOOGLE_CLIENT_ID', '')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', '')
        self.keys = []
        self.keys_until = 0

    def configured(self):
        if not all((self.client_id, self.client_secret, self.redirect_uri)):
            raise HTTPException(503, 'Google sign-in is unavailable. Please use SMS or try later.')
        allowed = {origin + '/api/auth/google/callback' for origin in self.auth.settings.origins}
        if self.redirect_uri not in allowed:
            raise HTTPException(503, 'Google sign-in configuration is unavailable.')

    def cookie(self, response, value):
        response.set_cookie(COOKIE, value, max_age=300, httponly=True,
                            secure=self.auth.settings.environment == 'production', samesite='lax', path='/api/auth/google')
        self.response_headers(response)

    @staticmethod
    def response_headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'

    async def login(self, request, *, link_user=None):
        self.configured()
        await self.auth.limit('google:' + (request.client.host if request.client else 'unknown'), 30, 3600)
        state, binding, nonce, verifier = [secrets.token_urlsafe(32) for _ in range(4)]
        await self.auth.db.auth_google_transactions.insert_one({
            '_id': self.auth.digest(state), 'binding': self.auth.digest(binding), 'nonce': nonce,
            'verifier': verifier, 'link_user_id': link_user['user_id'] if link_user else None, 'expires_at': self.auth.clock() + timedelta(minutes=5)})
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        response = RedirectResponse(AUTHORIZE + '?' + urlencode({
            'client_id': self.client_id, 'redirect_uri': self.redirect_uri, 'response_type': 'code',
            'scope': 'openid email profile', 'state': state, 'nonce': nonce,
            'code_challenge': challenge, 'code_challenge_method': 'S256'}), status_code=303)
        self.cookie(response, binding)
        return response

    async def claims(self, client, token, nonce):
        header = jwt.get_unverified_header(token)
        if header.get('alg') != 'RS256' or not isinstance(header.get('kid'), str):
            raise ValueError('Invalid signing key')
        # Cache trusted keys; refresh once for an unknown kid to support rotation.
        for attempt in range(2):
            if time.monotonic() >= self.keys_until or attempt:
                result = await client.get(JWKS)
                result.raise_for_status()
                self.keys = result.json()['keys']
                self.keys_until = time.monotonic() + 300
            key = next((k for k in self.keys if k.get('kid') == header['kid'] and k.get('kty') == 'RSA'), None)
            if key:
                break
        if not key:
            raise ValueError('Unknown signing key')
        claims = jwt.decode(token, jwt.PyJWK.from_dict(key).key, algorithms=['RS256'],
                            audience=self.client_id, issuer=['https://accounts.google.com', 'accounts.google.com'],
                            options={'require': ['exp', 'iat', 'iss', 'aud', 'sub', 'nonce']})
        if not isinstance(claims['sub'], str) or not 1 <= len(claims['sub']) <= 255:
            raise ValueError('Invalid subject')
        if not isinstance(claims['nonce'], str) or not hmac.compare_digest(claims['nonce'], nonce):
            raise ValueError('Invalid nonce')
        if isinstance(claims['aud'], list) and len(claims['aud']) > 1 and 'azp' not in claims:
            raise ValueError('Missing authorized party')
        if claims.get('azp', self.client_id) != self.client_id:
            raise ValueError('Invalid authorized party')
        return claims

    async def user(self, claims):
        identity = {'auth_provider': 'google', 'auth_subject': claims['sub']}
        uid = 'user_' + self.auth.digest('google:' + claims['sub'])[:24]
        now = self.auth.clock().isoformat()
        document = {**identity, 'user_id': uid, 'role': 'customer', 'status': 'active',
                    'name': str(claims.get('name', 'Customer'))[:100],
                    'email': str(claims.get('email', ''))[:254] if claims.get('email_verified') is True else '',
                    'onboarding_completed': True, 'created_at': now, 'updated_at': now}
        existing = await self.auth.db.users.find_one(identity)
        if existing:
            self.auth.ensure_active(existing)
            return existing
        email = document['email']
        if email:
            collision = await self.auth.db.users.find_one({
                'email': {'$regex': '^' + re.escape(email) + '$', '$options': 'i'}
            })
            if collision:
                raise ExistingAccountLinkRequired('Existing account requires explicit linking')
        try:
            await self.auth.db.users.update_one(identity, {'$setOnInsert': document}, upsert=True)
        except DuplicateKeyError:
            pass
        user = await self.auth.db.users.find_one(identity)
        if not user:
            raise ValueError('Unavailable identity')
        if user.get('role') not in ('customer', 'admin', 'owner'):
            raise ValueError('Unavailable identity')
        self.auth.ensure_active(user)
        await self.auth.db.wallets.update_one({'user_id': user['user_id']}, {'$setOnInsert': {'balance': 0.0}}, upsert=True)
        return user

    async def callback(self, request):
        response = RedirectResponse('/login?google_error=1', status_code=303)
        self.response_headers(response)
        response.delete_cookie(COOKIE, path='/api/auth/google', httponly=True,
                               secure=self.auth.settings.environment == 'production', samesite='lax')
        try:
            self.configured()
            state = request.query_params.get('state', '')
            binding = request.cookies.get(COOKIE, '')
            if not 20 <= len(state) <= 200 or not 20 <= len(binding) <= 200:
                return response
            # Atomic consumption prevents concurrent callbacks and replay, even on denial/failure.
            transaction = await self.auth.db.auth_google_transactions.find_one_and_delete({
                '_id': self.auth.digest(state), 'binding': self.auth.digest(binding),
                'expires_at': {'$gt': self.auth.clock()}})
            code = request.query_params.get('code', '')
            if not transaction or request.query_params.get('error') or not 1 <= len(code) <= 4096:
                return response
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                result = await client.post(TOKEN, data={'grant_type': 'authorization_code', 'code': code,
                    'client_id': self.client_id, 'client_secret': self.client_secret,
                    'redirect_uri': self.redirect_uri, 'code_verifier': transaction['verifier']})
                result.raise_for_status()
                claims = await self.claims(client, result.json()['id_token'], transaction['nonce'])
            if transaction.get('link_user_id'):
                current = await self.auth.authenticate(request)
                if current['user_id'] != transaction['link_user_id']:
                    raise ValueError('Linking session changed')
                identity = {'auth_provider': 'google', 'auth_subject': claims['sub']}
                existing = await self.auth.db.users.find_one(identity)
                if existing and existing['user_id'] != current['user_id']:
                    raise ValueError('Google identity already linked')
                if current.get('auth_subject') and (current.get('auth_provider') != 'google' or current.get('auth_subject') != claims['sub']):
                    raise ValueError('Account already linked to another identity')
                result = await self.auth.db.users.update_one({'_id': current['_id'], '$or': [{'auth_subject': {'$exists': False}}, identity]}, {'$set': identity})
                if result.matched_count != 1:
                    raise ValueError('Unable to link identity')
                response.headers['location'] = '/admin' if current.get('role') == 'admin' else '/owner' if current.get('role') == 'owner' else '/app'
            else:
                user = await self.user(claims)
                await self.auth.login_response(user, response, request)
                response.headers['location'] = '/login'
        except ExistingAccountLinkRequired:
            response.headers['location'] = '/login?google_error=link_required'
        except (DuplicateKeyError, HTTPException, httpx.HTTPError, jwt.PyJWTError, ValueError, KeyError, TypeError):
            # Never include provider error payloads, codes, tokens or secrets in errors/logs.
            pass
        return response
, '$options': 'i'}}):
            raise ExistingAccountLinkRequired('Existing account requires explicit linking')
        try:
            await self.auth.db.users.update_one(identity, {'$setOnInsert': document}, upsert=True)
        except DuplicateKeyError:
            pass
        user = await self.auth.db.users.find_one(identity)
        if not user:
            raise ValueError('Unavailable identity')
        if user.get('role') not in ('customer', 'admin', 'owner'):
            raise ValueError('Unavailable identity')
        self.auth.ensure_active(user)
        await self.auth.db.wallets.update_one({'user_id': user['user_id']}, {'$setOnInsert': {'balance': 0.0}}, upsert=True)
        return user

    async def callback(self, request):
        response = RedirectResponse('/login?google_error=1', status_code=303)
        self.response_headers(response)
        response.delete_cookie(COOKIE, path='/api/auth/google', httponly=True,
                               secure=self.auth.settings.environment == 'production', samesite='lax')
        try:
            self.configured()
            state = request.query_params.get('state', '')
            binding = request.cookies.get(COOKIE, '')
            if not 20 <= len(state) <= 200 or not 20 <= len(binding) <= 200:
                return response
            # Atomic consumption prevents concurrent callbacks and replay, even on denial/failure.
            transaction = await self.auth.db.auth_google_transactions.find_one_and_delete({
                '_id': self.auth.digest(state), 'binding': self.auth.digest(binding),
                'expires_at': {'$gt': self.auth.clock()}})
            code = request.query_params.get('code', '')
            if not transaction or request.query_params.get('error') or not 1 <= len(code) <= 4096:
                return response
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                result = await client.post(TOKEN, data={'grant_type': 'authorization_code', 'code': code,
                    'client_id': self.client_id, 'client_secret': self.client_secret,
                    'redirect_uri': self.redirect_uri, 'code_verifier': transaction['verifier']})
                result.raise_for_status()
                claims = await self.claims(client, result.json()['id_token'], transaction['nonce'])
            if transaction.get('link_user_id'):
                current = await self.auth.authenticate(request)
                if current['user_id'] != transaction['link_user_id']:
                    raise ValueError('Linking session changed')
                identity = {'auth_provider': 'google', 'auth_subject': claims['sub']}
                existing = await self.auth.db.users.find_one(identity)
                if existing and existing['user_id'] != current['user_id']:
                    raise ValueError('Google identity already linked')
                if current.get('auth_subject') and (current.get('auth_provider') != 'google' or current.get('auth_subject') != claims['sub']):
                    raise ValueError('Account already linked to another identity')
                result = await self.auth.db.users.update_one({'_id': current['_id'], '$or': [{'auth_subject': {'$exists': False}}, identity]}, {'$set': identity})
                if result.matched_count != 1:
                    raise ValueError('Unable to link identity')
                response.headers['location'] = '/admin' if current.get('role') == 'admin' else '/owner' if current.get('role') == 'owner' else '/app'
            else:
                user = await self.user(claims)
                await self.auth.login_response(user, response, request)
                response.headers['location'] = '/login'
        except ExistingAccountLinkRequired:
            response.headers['location'] = '/login?google_error=link_required'
        except (DuplicateKeyError, HTTPException, httpx.HTTPError, jwt.PyJWTError, ValueError, KeyError, TypeError):
            # Never include provider error payloads, codes, tokens or secrets in errors/logs.
            pass
        return response
