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

SETTINGS = AuthSettings('test-only-production-bootstrap-secret-12345', 'test', 'provider', False, ('https://example.test',))
ENV = {'MONGO_URL': 'mongodb://127.0.0.1:27027', 'DB_NAME': 'rushx_production', 'JWT_SECRET': SETTINGS.secret,
       'APP_ENV': 'production', 'OTP_MODE': 'provider', 'EXPOSE_DEMO_OTP': 'false', 'CORS_ORIGINS': 'https://example.test'}


@pytest.mark.parametrize('change', [
    {'DB_NAME': ''}, {'APP_ENV': ''}, {'OTP_MODE': 'demo'}, {'EXPOSE_DEMO_OTP': 'true'},
    {'CORS_ORIGINS': '*'}, {'JWT_SECRET': 'short'}, {'MONGO_URL': 'mongodb://localhost/other'},
    {'MONGO_URL': 'https://example.test'}, {'DB_NAME': 'other'},
])
def test_configuration_fails_closed(change):
    with patch.dict(os.environ, {**ENV, **change}, clear=True), pytest.raises(RuntimeError):
        configuration('rushx_production')


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
            # Real Mongo recovery after an interrupted build retains already-built
            # indexes, and an empty target can resume without dropping any.
            from production_cli import BootstrapFailure
            from services.safety_indexes import initialize_safety_indexes
            async def interrupted(target):
                await initialize_safety_indexes(target)
                raise RuntimeError('redacted driver failure')
            with patch('production_cli.initialize_safety_indexes', interrupted), pytest.raises(BootstrapFailure):
                await bootstrap(db, SETTINGS, True)
            partial = await bootstrap(db, SETTINGS)
            assert not partial['complete'] and partial['ready']
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
            count = await db.users.count_documents({})
            with pytest.raises(RuntimeError, match='empty'):
                await bootstrap(db, SETTINGS, True)
            assert (await bootstrap(db, SETTINGS, verify_existing=True))['complete']
            assert await db.users.count_documents({}) == count
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


@pytest.mark.parametrize('environment', ['production', 'test', 'development'])
def test_staging_is_never_an_operator_target(environment):
    env = {**ENV, 'APP_ENV': environment, 'DB_NAME': 'voltx_staging'}
    with patch.dict(os.environ, env, clear=True), pytest.raises(RuntimeError, match='voltx_staging'):
        configuration('voltx_staging')


@pytest.mark.parametrize('database', ['other_production', 'rushx_production_typo', 'rushx_bootstrap_test'])
def test_production_database_allowlist(database):
    with patch.dict(os.environ, {**ENV, 'DB_NAME': database}, clear=True), pytest.raises(RuntimeError, match='require rushx_production'):
        configuration(database)


def test_explicit_target_valid_and_no_environment_bypass_for_remote_mongo():
    with patch.dict(os.environ, ENV, clear=True):
        assert configuration('rushx_production')[1].environment == 'production'
    test_env = {**ENV, 'APP_ENV': 'test', 'DB_NAME': 'rushx_bootstrap_test'}
    with patch.dict(os.environ, test_env, clear=True):
        assert configuration('rushx_bootstrap_test')[1].environment == 'test'
    for change in [{'MONGO_URL': 'mongodb://remote.example.test'}, {'DB_NAME': 'rushx_production'}]:
        with patch.dict(os.environ, {**test_env, **change}, clear=True), pytest.raises(RuntimeError, match='loopback test database'):
            configuration(change.get('DB_NAME', 'rushx_bootstrap_test'))


@pytest.mark.parametrize('collection', ['users', 'chargers', 'auth_sessions', 'unexpected_collection'])
def test_nonempty_bootstrap_rejected_before_any_index_writes(collection):
    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).db
        await db[collection].insert_one({'fixture': True})
        for apply in [False, True]:
            with pytest.raises(RuntimeError, match='every collection to be empty'):
                await bootstrap(db, SETTINGS, apply)
        assert await db.payment_references.index_information() == {}
        assert await db[collection].count_documents({}) == 1
        with pytest.raises(RuntimeError, match='verify-existing'):
            await bootstrap(db, SETTINGS, verify_existing=True)
    asyncio.run(scenario())


def test_complete_populated_rerun_exception_is_read_only():
    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).db
        await bootstrap(db, SETTINGS, True)
        await enrollment(db)
        before = await db.users.find_one({})
        indexes = {c: await db[c].index_information() for c in await db.list_collection_names()}
        with pytest.raises(RuntimeError, match='empty'):
            await bootstrap(db, SETTINGS, True)
        with pytest.raises(RuntimeError, match='read-only'):
            await bootstrap(db, SETTINGS, True, verify_existing=True)
        result = await bootstrap(db, SETTINGS, verify_existing=True)
        assert result['complete'] and result['outcome'] == 'verified-existing'
        assert result['newly_ready'] == []
        assert await db.users.find_one({}) == before
        assert indexes == {c: await db[c].index_information() for c in await db.list_collection_names()}
    asyncio.run(scenario())


def test_partial_migration_report_redacts_and_supports_verified_recovery():
    from services.index_contract import ensure_index
    from production_cli import BootstrapFailure
    import json
    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).db
        async def fail_partway(db):
            for collection, keys, options in INDEXES[:3]:
                await ensure_index(db, collection, keys, options)
            raise RuntimeError('private-password customer@example.test mongodb://private')
        with patch('production_cli.initialize_safety_indexes', fail_partway), pytest.raises(BootstrapFailure) as error:
            await bootstrap(db, SETTINGS, True)
        message = str(error.value)
        assert not any(secret in message for secret in ['private-password', 'customer@example.test', 'mongodb://'])
        report = json.loads(message)
        assert report['stage'] == 'safety-indexes' and report['outcome'] == 'failed'
        assert len(report['newly_ready']) == 3
        assert len(report['missing']) == len(INDEXES) - 3
        assert not report['conflicting'] and not report['unreadable']
        inspected = await bootstrap(db, SETTINGS)
        assert len(inspected['ready']) == 3
        assert inspected['missing'] == report['missing']
        recovered = await bootstrap(db, SETTINGS, True)
        assert recovered['complete'] and len(recovered['newly_ready']) == len(INDEXES)-3
        assert (await bootstrap(db, SETTINGS))['complete']
        for collection in await db.list_collection_names():
            assert await db[collection].count_documents({}) == 0
    asyncio.run(scenario())


def test_unreadable_index_reports_do_not_claim_recovery_success():
    from production_cli import index_report
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    async def scenario():
        db = {collection: SimpleNamespace(index_information=AsyncMock(side_effect=RuntimeError('secret')))
              for collection, _, _ in INDEXES}
        report = await index_report(db)
        assert not report['complete'] and len(report['unreadable']) == len(INDEXES)
        assert 'secret' not in str(report)
    asyncio.run(scenario())


def test_concurrent_data_write_cannot_report_bootstrap_success():
    import json
    from production_cli import BootstrapFailure
    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True).db
        original = AuthService.initialize
        async def initialize_then_write(service, **kwargs):
            await original(service, **kwargs)
            await db.chargers.insert_one({'private': 'customer data'})
        with patch.object(AuthService, 'initialize', initialize_then_write), pytest.raises(BootstrapFailure) as error:
            await bootstrap(db, SETTINGS, True)
        report = json.loads(str(error.value))
        assert report['outcome'] == 'failed' and report['stage'] == 'post-empty-check'
        assert report['complete'] and report['empty_precondition'] is False
        assert 'customer data' not in str(error.value)
        with pytest.raises(RuntimeError, match='empty'):
            await bootstrap(db, SETTINGS, True)
        assert (await bootstrap(db, SETTINGS, verify_existing=True))['outcome'] == 'verified-existing'
    asyncio.run(scenario())


@pytest.mark.parametrize('database,environment', [('voltx_staging', 'test'), ('voltx_staging', 'production'), ('wrong', 'production')])
def test_direct_bootstrap_also_guards_target_before_database_operations(database, environment):
    from dataclasses import replace
    async def scenario():
        db = AsyncMongoMockClient(tz_aware=True)[database]
        for apply in [False, True]:
            with pytest.raises(RuntimeError, match='target forbidden'):
                await bootstrap(db, replace(SETTINGS, environment=environment), apply)
        assert await db.list_collection_names() == []
    asyncio.run(scenario())
