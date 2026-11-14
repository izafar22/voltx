"""Live integration-test adapter for the challenge + cookie auth contract."""
import secrets
import time
import requests

ORIGIN = 'http://localhost:3000'
_cache = {}


def new_phone():
    return '+919' + ''.join(str(secrets.randbelow(10)) for _ in range(9))


def login_session(api, phone, name=None):
    key = (api, phone)
    if key in _cache:
        return _cache[key]
    session = requests.Session()
    session.headers['Origin'] = ORIGIN
    requested = session.post(api+'/auth/request-otp', json={'phone':phone}, timeout=30)
    # Two xdist workers may both need a seeded role; honor the real cooldown.
    if requested.status_code == 429 and requested.headers.get('Retry-After') == '60':
        time.sleep(60)
        requested = session.post(api+'/auth/request-otp', json={'phone':phone}, timeout=30)
    assert requested.status_code == 200, 'OTP request failed: '+str(requested.status_code)
    response = session.post(api+'/auth/verify-otp', json={'phone':phone,'challenge_id':requested.json()['challenge_id'],'otp':'123456'}, timeout=30)
    assert response.status_code == 200, 'OTP verification failed: '+str(response.status_code)
    data = response.json()
    if data.get('registration_required'):
        response = session.post(api+'/auth/register-customer', headers={'Authorization':'Bearer '+data['registration_token']}, json={'name':name or 'Integration Customer'}, timeout=30)
        assert response.status_code == 200, 'Registration failed: '+str(response.status_code)
        data = response.json()
    _cache[key] = session, data['user']
    return _cache[key]


def login_headers(api, phone, name=None):
    session, _ = login_session(api, phone, name)
    return {'Origin': ORIGIN, 'Cookie': '; '.join(f'{key}={value}' for key,value in session.cookies.items())}
