import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")

_base = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not _base:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = _base.rstrip("/")

MONGO_URL = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")
ADMIN_EMAIL = "crazycoder4192@gmail.com"


def _iso(dt):
    return dt.isoformat()


@pytest.fixture(scope="session")
def mongo_db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="session")
def customer_session(mongo_db):
    """Create a TEST_ customer user + session directly in Mongo (per /app/auth_testing.md)."""
    uid = "TEST_user_" + uuid.uuid4().hex[:10]
    token = "TEST_session_" + uuid.uuid4().hex[:16]
    email = f"TEST_{uuid.uuid4().hex[:6]}@example.com"
    mongo_db.users.insert_one({
        "user_id": uid, "email": email, "name": "TEST Customer", "picture": "",
        "role": "customer", "created_at": _iso(datetime.now(timezone.utc)),
    })
    mongo_db.user_sessions.insert_one({
        "user_id": uid, "session_token": token,
        "expires_at": _iso(datetime.now(timezone.utc) + timedelta(days=7)),
        "created_at": _iso(datetime.now(timezone.utc)),
    })
    yield {"user_id": uid, "token": token, "email": email}
    # teardown
    mongo_db.user_sessions.delete_many({"user_id": uid})
    mongo_db.users.delete_many({"user_id": uid})
    mongo_db.bookings.delete_many({"user_id": uid})
    mongo_db.subscriptions.delete_many({"user_id": uid})
    mongo_db.invoices.delete_many({"user_id": uid})
    mongo_db.quotes.delete_many({"user_id": uid})


@pytest.fixture(scope="session")
def admin_session(mongo_db):
    admin = mongo_db.users.find_one({"email": ADMIN_EMAIL})
    if not admin:
        pytest.fail("Admin user not seeded")
    token = "TEST_admin_session_" + uuid.uuid4().hex[:16]
    mongo_db.user_sessions.insert_one({
        "user_id": admin["user_id"], "session_token": token,
        "expires_at": _iso(datetime.now(timezone.utc) + timedelta(days=7)),
        "created_at": _iso(datetime.now(timezone.utc)),
    })
    yield {"user_id": admin["user_id"], "token": token, "role": admin.get("role")}
    mongo_db.user_sessions.delete_one({"session_token": token})


@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def cust_client(customer_session):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json",
                      "Authorization": f"Bearer {customer_session['token']}"})
    return s


@pytest.fixture(scope="session")
def admin_client(admin_session):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json",
                      "Authorization": f"Bearer {admin_session['token']}"})
    return s
