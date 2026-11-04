"""Explicit operator commands. Never imports server, loads .env, seeds, or drops indexes."""
import argparse
import asyncio
import getpass
import os
import re
import sys
from urllib.parse import urlsplit, unquote

from motor.motor_asyncio import AsyncIOMotorClient
try:
    from .auth_service import AuthService, AuthSettings
    from .production_admin import provision_admin
    from .services.index_contract import VERSION, INDEXES, inspect_indexes
    from .services.safety_indexes import initialize_safety_indexes
except ImportError:
    from auth_service import AuthService, AuthSettings
    from production_admin import provision_admin
    from services.index_contract import VERSION, INDEXES, inspect_indexes
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
    return uri, settings


async def verify_indexes(db, require_complete=True):
    missing = 0
    for collection, keys, options in INDEXES:
        if not inspect_indexes(await db[collection].index_information(), keys, options):
            missing += 1
    if require_complete and missing:
        raise RuntimeError('Required indexes are missing; run the reviewed bootstrap first')
    return missing


async def bootstrap(db, settings, apply=False):
    # Preflight every definition before creating anything. Index builds can fail
    # partway (e.g. duplicate data); reruns resume safely without dropping indexes.
    missing = await verify_indexes(db, require_complete=False)
    if not apply:
        return {'version': VERSION, 'missing_indexes': missing}
    await initialize_safety_indexes(db)
    await AuthService(db, settings).initialize(migrate_legacy=False)
    await verify_indexes(db)
    return {'version': VERSION, 'missing_indexes': 0}


async def execute(args):
    uri, settings = configuration(args.database)
    if args.apply and args.confirm_database != args.database:
        raise RuntimeError('Writes require --confirm-database matching --database and DB_NAME')
    client = AsyncIOMotorClient(uri, tz_aware=True, serverSelectionTimeoutMS=10000)
    try:
        db = client[args.database]
        if args.command == 'bootstrap':
            result = await bootstrap(db, settings, args.apply)
            print(f"Bootstrap v{result['version']}: missing_indexes={result['missing_indexes']}")
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
