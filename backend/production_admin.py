"""Operator-only promotion after a verified Google first-login enrollment."""
import re
import secrets
from datetime import datetime, timedelta, timezone
from pymongo import ReturnDocument


async def provision_admin(db, subject, email, name, promote_existing=False, now=None):
    now = now or datetime.now(timezone.utc)
    if (not isinstance(subject, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,255}', subject)
            or not isinstance(email, str) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(email) > 254
            or not isinstance(name, str) or not 2 <= len(name.strip()) <= 100
            or any(ord(c) < 32 for c in name + email)):
        raise RuntimeError('Invalid operator identity input')
    identity = {'auth_provider': 'google', 'auth_subject': subject}
    matches = await db.users.find(identity).to_list(length=2)
    if len(matches) != 1:
        raise RuntimeError('Exactly one verified Google enrollment is required')
    user = matches[0]
    if user.get('status') != 'active' or user.get('google_verified_email', '').casefold() != email.casefold():
        raise RuntimeError('Active verified Google enrollment does not match operator input')
    # Same email on a different account is ambiguous; never merge or link by email.
    others = await db.users.count_documents({'_id': {'$ne': user['_id']}, '$or': [
        {'email': {'$regex': '^' + re.escape(email) + '$', '$options': 'i'}},
        {'google_verified_email': {'$regex': '^' + re.escape(email) + '$', '$options': 'i'}}]})
    if others:
        raise RuntimeError('Identity conflict requires explicit operator review; no accounts merged')
    marker = user.get('admin_provisioning', {})
    if user.get('role') == 'admin' and marker.get('version') == 1 and marker.get('email') == email.casefold() and user.get('name') == name.strip():
        return 'unchanged'
    if not promote_existing or user.get('role') != 'customer' or user.get('phone') or marker:
        raise RuntimeError('Explicit promotion of a Google-only customer enrollment is required')
    try:
        verified_at = datetime.fromisoformat(user['google_verified_at'])
        if not now - timedelta(hours=24) <= verified_at <= now + timedelta(seconds=30):
            raise ValueError()
    except (KeyError, ValueError, TypeError):
        raise RuntimeError('A fresh verified Google login within 24 hours is required') from None
    changed = await db.users.find_one_and_update({
        **identity, '_id': user['_id'], 'role': 'customer', 'status': 'active',
        'phone': {'$exists': False}, 'admin_provisioning': {'$exists': False},
        'google_verified_at': user['google_verified_at'], 'google_verified_email': user['google_verified_email'],
    }, {'$set': {'role': 'admin', 'name': name.strip(), 'auth_epoch': secrets.token_hex(24),
                 'admin_provisioning': {'version': 1, 'email': email.casefold(), 'at': now.isoformat()},
                 'updated_at': now.isoformat()}}, return_document=ReturnDocument.AFTER)
    if not changed:
        current = await db.users.find_one(identity)
        if current and current.get('role') == 'admin' and current.get('admin_provisioning', {}).get('email') == email.casefold() and current.get('name') == name.strip():
            return 'unchanged'
        raise RuntimeError('Enrollment changed concurrently; rerun after operator review')
    # Epoch mismatch already invalidates every earlier session, even if deletion fails.
    await db.auth_sessions.delete_many({'user_id': changed['user_id']})
    return 'provisioned'
