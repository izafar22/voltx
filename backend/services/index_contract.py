"""Version 1 index contract shared by startup, bootstrap and verification."""
VERSION = 1
SAFETY_INDEXES = [
    ('payment_references', [('repair_id', 1), ('receipt.idempotency_key', 1)],
     {'unique': True, 'name': 'repair_payment_idempotency'}),
    ('repair_requests', [('creation_key', 1)], {'unique': True, 'sparse': True, 'name': 'creation_key_1'}),
] + [('repair_requests', prefix + [('created_at', -1), ('id', -1)], {})
     for prefix in ([], [('user_id', 1)], [('charger_id', 1)], [('status', 1)])]
AUTH_INDEXES = [
    ('users', [('phone', 1)], {'unique': True, 'name': 'auth_phone_partial_unique',
                            'partialFilterExpression': {'phone': {'$type': 'string'}}}),
    ('users', [('auth_provider', 1), ('auth_subject', 1)], {'unique': True, 'name': 'auth_provider_subject_unique',
        'partialFilterExpression': {'auth_provider': {'$type': 'string'}, 'auth_subject': {'$type': 'string'}}}),
    ('users', [('user_id', 1)], {'unique': True, 'name': 'auth_user_id_unique'}),
    ('wallets', [('user_id', 1)], {'unique': True, 'name': 'auth_wallet_user_unique'}),
] + [(collection, [('expires_at', 1)], {'expireAfterSeconds': 0}) for collection in
     ('auth_challenges', 'auth_limits', 'auth_sessions', 'auth_registrations', 'auth_google_transactions')
] + [('auth_challenges', [('phone', 1)], {})]
INDEXES = SAFETY_INDEXES + AUTH_INDEXES


def index_name(keys, options):
    return options.get('name') or '_'.join(f'{key}_{direction}' for key, direction in keys)


def equivalent(actual, keys, options):
    return (list(actual.get('key', [])) == keys
            and all(bool(actual.get(k, False)) == bool(options.get(k, False)) for k in ('unique', 'sparse', 'hidden'))
            and actual.get('partialFilterExpression') == options.get('partialFilterExpression')
            and actual.get('expireAfterSeconds') == options.get('expireAfterSeconds')
            and actual.get('collation') is None)


def inspect_indexes(information, keys, options, allow_legacy_phone=False):
    """Accept equivalent indexes under any name; reject drift without mutation."""
    found = False
    for name, actual in information.items():
        if equivalent(actual, keys, options):
            found = True
        elif name == index_name(keys, options) or list(actual.get('key', [])) == keys:
            if allow_legacy_phone and keys == [('phone', 1)] and actual.get('unique') and not actual.get('partialFilterExpression'):
                continue
            raise RuntimeError('Index definition conflict; operator review required (no indexes dropped)')
    return found


async def ensure_index(db, collection, keys, options, allow_legacy_phone=False):
    information = await db[collection].index_information()
    if not inspect_indexes(information, keys, options, allow_legacy_phone):
        await db[collection].create_index(keys, **options)
