"""Offline configuration/unit checks and disposable loopback Mongo integration."""
import asyncio
import os
import secrets
from datetime import timedelta
from unittest.mock import patch

import pytest
from mongomock_motor import AsyncMongoMockClient
from motor.motor_asyncio import AsyncIOMotorClient
from auth_service import AuthService, AuthSettings
from production_cli import configuration, bootstrap, verify_indexes
from production_admin import provision_admin
from services.index_contract import INDEXES, equivalent

SETTINGS = AuthSettings('test-only-production-bootstrap-secret-12345', 'production', 'provider', False, ('https://example.test',))
ENV = {'MONGO_URL': 'mongodb://127.0.0.1:27027', 'DB_NAME': 'rushx_bootstrap_test', 'JWT_SECRET': SETTINGS.secret,
       'APP_ENV': 'production', 'OTP_MODE': 'provider', 'EXPOSE_DEMO_OTP': 'false', 'CORS_ORIGINS': 'https://example.test'}


@pytest.mark.parametrize('change', [
    {'DB_NAME': ''}, {'APP_ENV': ''}, {'OTP_MODE': 'demo'}, {'EXPOSE_DEMO_OTP': 'true'},
    {'CORS_ORIGINS': '*'}, {'JWT_SECRET': 'short'}, {'MONGO_URL': 'mongodb://localhost/other'},
    {'MONGO_URL': 'https://example.test'}, {'DB_NAME': 'other'},
])
def test_configuration_fails_closed(change):
    with patch.dict(os.environ, {**ENV, **change}, clear=True), pytest.raises(RuntimeError):
        configuration('rushx_bootstrap_test')


@pytest.mark.parametrize('database', ['admin', 'local', 'config', '../db', 'bad.name', ''])
def test_invalid_database(database):
    with patch.dict(os.environ, {**ENV, 'DB_NAME': database}, clear=True), pytest.raises(RuntimeError):
        configuration(database)


def test_index_options_not_just_names():
    for _, keys, options in INDEXES:
        actual = {'key': keys, **options}
        assert equivalent(actual, keys, options)
        for prop in ['unique', 'sparse', 'expireAfterSeconds', 'partialFilterExpression']:
            changed = dict(actual)
            changed[prop] = not actual.get(prop) if prop in ['unique', 'sparse'] else (60 if prop == 'expireAfterSeconds' else {'wrong': {'$exists': True}})
            assert not equivalent(changed, keys, options)


def test_repeat_bootstrap_no_records_and_reject_index_drift():
    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).db
        assert (await bootstrap(db, SETTINGS))['missing_indexes'] == len(INDEXES)
        assert await db.list_collection_names() == []
        for _ in range(2):
            assert (await bootstrap(db, SETTINGS, apply=True))['missing_indexes'] == 0
        for collection in await db.list_collection_names():
            assert await db[collection].count_documents({}) == 0
        before = await db.users.index_information()
        await db.users.drop_index('auth_user_id_unique')  # test fixture drift, disposable only
        await db.users.create_index('user_id', name='auth_user_id_unique', unique=False)
        with pytest.raises(RuntimeError, match='conflict'):
            await bootstrap(db, SETTINGS, apply=True)
        assert (await db.users.index_information())['auth_user_id_unique'].get('unique') is not True
        assert before['auth_user_id_unique']['unique']
    asyncio.run(scenario())


async def enrollment(db, subject='verified-sub', email='operator@example.test'):
    service = AuthService(db, SETTINGS)
    return await service.google.user({'sub': subject, 'email': email, 'email_verified': True, 'name': 'Operator'})


def test_provision_requires_verified_subject_explicit_promotion_and_revokes_sessions():
    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).db
        await bootstrap(db, SETTINGS, True)
        user = await enrollment(db)
        await db.auth_sessions.insert_one({'_id': 'old', 'user_id': user['user_id']})
        with pytest.raises(RuntimeError):
            await provision_admin(db, 'verified-sub', 'operator@example.test', 'Operator')
        for subject, email in [('other', 'operator@example.test'), ('verified-sub', 'wrong@example.test')]:
            with pytest.raises(RuntimeError):
                await provision_admin(db, subject, email, 'Operator', True)
        results = await asyncio.gather(*[provision_admin(db, 'verified-sub', 'operator@example.test', 'Operator', True) for _ in range(4)])
        assert results.count('provisioned') == 1
        assert results.count('unchanged') == 3
        admin = await db.users.find_one({'user_id': user['user_id']})
        assert admin['role'] == 'admin' and admin['auth_subject'] == 'verified-sub' and admin['auth_epoch']
        assert await db.auth_sessions.count_documents({}) == 0
        assert await provision_admin(db, 'verified-sub', 'operator@example.test', 'Operator') == 'unchanged'
        assert await db.users.count_documents({}) == 1
    asyncio.run(scenario())


@pytest.mark.parametrize('case', ['unverified', 'inactive', 'phone', 'owner', 'stale', 'conflict'])
def test_unsafe_enrollments_are_not_promoted(case):
    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).db
        await bootstrap(db, SETTINGS, True)
        user = await enrollment(db)
        changes = {'unverified': {'google_verified_email': ''}, 'inactive': {'status': 'disabled'},
                   'phone': {'phone': '+919876543210'}, 'owner': {'role': 'owner'},
                   'stale': {'google_verified_at': (AuthService(db, SETTINGS).clock()-timedelta(days=2)).isoformat()}}
        if case == 'conflict':
            await db.users.insert_one({'user_id': 'other', 'email': 'OPERATOR@example.test', 'role': 'customer'})
        else:
            await db.users.update_one({'user_id': user['user_id']}, {'$set': changes[case]})
        with pytest.raises(RuntimeError):
            await provision_admin(db, 'verified-sub', 'operator@example.test', 'Operator', True)
        assert await db.users.count_documents({'role': 'admin'}) == 0
    asyncio.run(scenario())


def test_real_mongo_repeat_bootstrap_and_constraints():
    async def scenario():
        # New test never falls back to .env or Atlas. CI passes its loopback service.
        uri = os.environ.get('MONGO_URL', '')
        from urllib.parse import urlsplit
        if urlsplit(uri).hostname not in ('localhost', '127.0.0.1', '::1'):
            pytest.fail('Integration test requires explicitly configured loopback MongoDB')
        client = AsyncIOMotorClient(uri, tz_aware=True, serverSelectionTimeoutMS=5000)
        name = 'rushx_bootstrap_test_' + secrets.token_hex(10)
        db = client[name]
        try:
            # Representative pre-created ordinary query indexes under arbitrary names.
            for number, (collection, keys, options) in enumerate(INDEXES):
                if collection == 'repair_requests' and not options:
                    await db[collection].create_index(keys, name='existing_' + str(number))
            await bootstrap(db, SETTINGS, True)
            first = {c: await db[c].index_information() for c in await db.list_collection_names()}
            await bootstrap(db, SETTINGS, True)
            assert first == {c: await db[c].index_information() for c in await db.list_collection_names()}
            for c in first:
                assert await db[c].count_documents({}) == 0
            from pymongo.errors import DuplicateKeyError
            await db.users.insert_one({'user_id': 'one', 'auth_provider': 'google', 'auth_subject': 'one'})
            await db.users.insert_one({'user_id': 'two', 'auth_provider': 'google', 'auth_subject': 'two'})
            with pytest.raises(DuplicateKeyError):
                await db.users.insert_one({'user_id': 'three', 'auth_provider': 'google', 'auth_subject': 'one'})
            await db.users.insert_one({'user_id': 'phone-one', 'phone': '+919876543210'})
            with pytest.raises(DuplicateKeyError):
                await db.users.insert_one({'user_id': 'phone-two', 'phone': '+919876543210'})
            await verify_indexes(db)
        finally:
            await client.drop_database(name)
            client.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('collection,keys,options', [
    ('users', [('phone', 1)], {'unique': True}),
    ('repair_requests', [('creation_key', 1)], {'unique': True, 'sparse': False}),
    ('auth_sessions', [('expires_at', 1)], {'expireAfterSeconds': 60}),
    ('users', [('auth_provider', 1), ('auth_subject', 1)], {'unique': True, 'partialFilterExpression': {'auth_provider': {'$exists': True}}}),
])
def test_conflicting_definitions_abort_preflight_without_drops(collection, keys, options):
    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).db
        await db[collection].create_index(keys, name='operator_existing', **options)
        before = await db[collection].index_information()
        with pytest.raises(RuntimeError):
            await bootstrap(db, SETTINGS, True)
        assert await db[collection].index_information() == before
        assert await db.payment_references.index_information() == {}
    asyncio.run(scenario())


def test_cli_invalid_configuration_redacts_credentials_and_does_not_connect():
    import subprocess
    import sys
    env = {**os.environ, **ENV, 'DB_NAME': 'wrong', 'MONGO_URL': 'mongodb://private-user:private-password@127.0.0.1:1'}
    result = subprocess.run([sys.executable, '-m', 'production_cli', 'bootstrap', '--database', 'rushx_bootstrap_test', '--apply'], env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert 'private-user' not in result.stderr and 'private-password' not in result.stderr
    assert result.stdout == ''
