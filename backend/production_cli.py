"""Explicit operator commands. Never imports server, loads .env, seeds, or drops indexes."""
import argparse
import asyncio
import getpass
import json
import os
import re
import sys
from urllib.parse import urlsplit, unquote

from motor.motor_asyncio import AsyncIOMotorClient
try:
    from .auth_service import AuthService, AuthSettings
    from .production_admin import provision_admin
    from .services.index_contract import VERSION, INDEXES, inspect_indexes, index_name
    from .services.safety_indexes import initialize_safety_indexes
except ImportError:
    from auth_service import AuthService, AuthSettings
    from production_admin import provision_admin
    from services.index_contract import VERSION, INDEXES, inspect_indexes, index_name
    from services.safety_indexes import initialize_safety_indexes



def configuration(database):
    required = ('MONGO_URL', 'DB_NAME', 'JWT_SECRET', 'APP_ENV', 'OTP_MODE', 'CORS_ORIGINS')
    if any(not os.environ.get(key) for key in required):
        raise RuntimeError('Explicit database and authentication settings are required')
    if (not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,62}', database or '')
            or database.lower() in ('admin', 'config', 'local')
            or database != os.environ['DB_NAME']):
        raise RuntimeError('Explicit database must be valid and exactly match DB_NAME')
    uri = os.environ['MONGO_URL']
    try:
        parsed = urlsplit(uri)
        uri_db = unquote(parsed.path.lstrip('/'))
        if parsed.scheme not in ('mongodb', 'mongodb+srv') or not parsed.netloc or (uri_db and uri_db != database):
            raise ValueError()
    except ValueError:
        raise RuntimeError('MongoDB URI is invalid or selects a different database') from None
    settings = AuthSettings.from_env()
    settings.validate()
    # Bootstrap must never enable seeded/demo identities, including on test targets.
    if settings.otp_mode != 'provider' or settings.expose_demo:
        raise RuntimeError('Operator commands require provider OTP with demo exposure disabled')
    if database.lower() == 'voltx_staging':
        raise RuntimeError('Operator commands must never target voltx_staging')
    if settings.environment == 'production':
        if database != 'rushx_production':
            raise RuntimeError('Production operator commands require rushx_production')
    elif (parsed.hostname not in ('localhost', '127.0.0.1', '::1')
          or not re.fullmatch(r'rushx_bootstrap_test(?:_[A-Za-z0-9_-]+)?', database)):
        raise RuntimeError('Non-production operator commands require a loopback test database')
    return uri, settings


async def index_report(db):
    report = {'version': VERSION, 'ready': [], 'missing': [], 'conflicting': [], 'unreadable': []}
    for collection, keys, options in INDEXES:
        identity = collection + '/' + index_name(keys, options)
        try:
            information = await db[collection].index_information()
        except Exception:
            report['unreadable'].append(identity)
            continue
        try:
            present = inspect_indexes(information, keys, options)
        except RuntimeError:
            report['conflicting'].append(identity)
        else:
            report['ready' if present else 'missing'].append(identity)
    report['missing_indexes'] = len(report['missing'])
    report['complete'] = not any(report[k] for k in ('missing', 'conflicting', 'unreadable'))
    return report


class BootstrapFailure(RuntimeError):
    def __init__(self, stage, before, after):
        # Only static contract identifiers/counts, never driver errors, URIs,
        # actual collection/index names supplied by data, or document contents.
        report = {**after, 'stage': stage, 'outcome': 'failed',
                  'newly_ready': sorted(set(after['ready']) - set(before['ready'])),
                  'empty_precondition': False if stage == 'post-empty-check' else 'recheck-required',
                  'recovery': 'Keep writers stopped. Inspect this report; rerun read-only bootstrap on the empty target before applying again. No automatic rollback.'}
        super().__init__(json.dumps(report, sort_keys=True))


async def verify_indexes(db, require_complete=True):
    report = await index_report(db)
    if report['conflicting'] or report['unreadable'] or (require_complete and not report['complete']):
        raise BootstrapFailure('verification', report, report)
    return report['missing_indexes']


async def bootstrap(db, settings, apply=False, verify_existing=False):
    # Defense in depth for direct callers, in addition to CLI validation before
    # client construction. Merely reading db.name performs no database operation.
    if db.name.lower() == 'voltx_staging' or (settings.environment == 'production' and db.name != 'rushx_production'):
        raise RuntimeError('Bootstrap target forbidden; production requires rushx_production and staging is never allowed')
    before = await index_report(db)
    if before['conflicting'] or before['unreadable']:
        raise BootstrapFailure('preflight', before, before)
    if verify_existing:
        if apply:
            raise RuntimeError('--verify-existing is read-only and cannot be combined with --apply')
        if not before['complete']:
            raise BootstrapFailure('verify-existing', before, before)
        return {**before, 'outcome': 'verified-existing', 'newly_ready': [], 'empty_precondition': 'not-required-read-only'}
    # Every collection, including unknown collections and auth transient records,
    # must have zero documents. No migration marker is exempted or written.
    for collection in await db.list_collection_names():
        if await db[collection].count_documents({}, limit=1):
            raise RuntimeError('Bootstrap requires every collection to be empty; use --verify-existing only for read-only verification of a complete migration')
    if not apply:
        return {**before, 'outcome': 'inspected-empty', 'newly_ready': [], 'empty_precondition': True}
    stage = 'safety-indexes'
    try:
        await initialize_safety_indexes(db)
        stage = 'auth-indexes'
        await AuthService(db, settings).initialize(migrate_legacy=False)
        stage = 'post-verification'
        await verify_indexes(db)
        # Detect concurrent writes before reporting success. Operator must keep
        # services/workers stopped; this is not a cross-collection write lock.
        stage = 'post-empty-check'
        for collection in await db.list_collection_names():
            if await db[collection].count_documents({}, limit=1):
                raise RuntimeError('Concurrent data write')
    except Exception:
        raise BootstrapFailure(stage, before, await index_report(db)) from None
    after = await index_report(db)
    if not after['complete']:
        raise BootstrapFailure('post-verification', before, after)
    return {**after, 'outcome': 'applied-empty', 'empty_precondition': True,
            'newly_ready': sorted(set(after['ready']) - set(before['ready']))}


async def execute(args):
    uri, settings = configuration(args.database)
    if args.verify_existing and args.command != 'bootstrap':
        raise RuntimeError('--verify-existing is only valid for bootstrap')
    if args.verify_existing and args.apply:
        raise RuntimeError('--verify-existing is read-only and cannot be combined with --apply')
    if args.apply and args.confirm_database != args.database:
        raise RuntimeError('Writes require --confirm-database matching --database and DB_NAME')
    client = AsyncIOMotorClient(uri, tz_aware=True, serverSelectionTimeoutMS=10000)
    try:
        db = client[args.database]
        if args.command == 'bootstrap':
            result = await bootstrap(db, settings, args.apply, args.verify_existing)
            print(json.dumps(result, sort_keys=True))
        else:
            if not args.apply:
                raise RuntimeError('Provisioning requires explicit --apply and database confirmation')
            await verify_indexes(db)
            if not sys.stdin.isatty():
                raise RuntimeError('Provisioning requires an interactive terminal for hidden identity input')
            # No PII in shell arguments/history/process lists, stdout, logs or artifacts.
            subject = getpass.getpass('Verified Google subject (hidden): ')
            email = getpass.getpass('Verified Google email (hidden): ')
            name = getpass.getpass('Administrator name (hidden): ')
            result = await provision_admin(db, subject, email, name, args.promote_existing_customer)
            print('Administrator provisioning: ' + result)
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('bootstrap', 'provision-admin'))
    parser.add_argument('--database', required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--verify-existing', action='store_true')
    parser.add_argument('--confirm-database')
    parser.add_argument('--promote-existing-customer', action='store_true')
    args = parser.parse_args()
    try:
        asyncio.run(execute(args))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        # Driver exceptions can contain URI credentials and document contents.
        print('Operation failed; review connectivity, permissions and data/index conflicts privately. No automatic cleanup performed.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
