"""Phase 2 backend tests: customer repair request creation flow (as exercised by the UI)
plus quick regression on existing endpoints. Uses the public REACT_APP_BACKEND_URL.
"""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

_env = dotenv_values("/app/frontend/.env")
_base = os.environ.get("REACT_APP_BACKEND_URL") or _env.get("REACT_APP_BACKEND_URL")
if not _base:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE = _base.rstrip("/") + "/api"

OTP = "123456"
OWNER_PHONE = "+919000000002"
ADMIN_PHONE = "+919000000001"
CUSTOMER_PHONE = "+919000000003"

TINY_PNG = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
)


def login(phone, name=None):
    requests.post(f"{BASE}/auth/request-otp", json={"phone": phone}, timeout=30)
    body = {"phone": phone, "otp": OTP}
    if name:
        body["name"] = name
    r = requests.post(f"{BASE}/auth/verify-otp", json=body, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def new_customer():
    return login("+9197" + uuid.uuid4().hex[:8], "TEST_Phase2")


@pytest.fixture(scope="module")
def cust():
    return login(CUSTOMER_PHONE)


@pytest.fixture(scope="module")
def owner():
    return login(OWNER_PHONE)


@pytest.fixture(scope="module")
def admin():
    return login(ADMIN_PHONE)


created = []


@pytest.fixture(scope="module", autouse=True)
def cleanup(admin):
    yield
    # best effort: no delete endpoint exists; cancel created repairs
    for rid, h in created:
        requests.patch(f"{BASE}/repairs/{rid}/status", headers=h, json={"status": "CANCELLED"}, timeout=30)


# --- Repair creation flow used by /repairs/new (Other charger) ---
class TestCustomerCreateFlow:
    def test_create_other_charger_then_awaiting_shipment(self, cust):
        r = requests.post(f"{BASE}/repairs", headers=cust, json={
            "customer_type": "RETAIL",
            "problem_description": "TEST_Phase2 charger does not power on",
            "reported_category": "Not powering on",
            "photos": [TINY_PNG],
            "charger_info": {"brand": "TEST_Delta", "model": "AC Mini 7.4", "charger_type": "AC",
                             "serial_number": "SN123", "power_rating": "7.4 kW"},
        }, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        created.append((d["id"], cust))
        assert d["status"] == "REQUESTED"
        assert d["repair_request_number"].startswith("REP-")
        assert d["charger_info"]["brand"] == "TEST_Delta"
        assert d["photos"] == [TINY_PNG]
        assert "_id" not in d

        p = requests.patch(f"{BASE}/repairs/{d['id']}/status", headers=cust,
                           json={"status": "AWAITING_SHIPMENT"}, timeout=30)
        assert p.status_code == 200, p.text
        assert p.json()["status"] == "AWAITING_SHIPMENT"

        g = requests.get(f"{BASE}/repairs/{d['id']}", headers=cust, timeout=30)
        assert g.status_code == 200
        got = g.json()
        assert got["status"] == "AWAITING_SHIPMENT"
        assert got["problem_description"] == "TEST_Phase2 charger does not power on"
        assert got["reported_category"] == "Not powering on"
        assert len(got["photos"]) == 1

    def test_not_sure_type_null_accepted(self, cust):
        r = requests.post(f"{BASE}/repairs", headers=cust, json={
            "customer_type": "RETAIL", "problem_description": "TEST_Phase2 not sure type",
            "charger_info": {"brand": "TEST_Generic", "model": "X1", "charger_type": None},
        }, timeout=30)
        assert r.status_code == 200, r.text
        created.append((r.json()["id"], cust))
        assert r.json()["charger_info"].get("charger_type") is None

    def test_invalid_charger_type_rejected(self, cust):
        r = requests.post(f"{BASE}/repairs", headers=cust, json={
            "customer_type": "RETAIL", "problem_description": "TEST_Phase2 bad type",
            "charger_info": {"brand": "TEST_B", "model": "M", "charger_type": "NOT_SURE"},
        }, timeout=30)
        assert r.status_code in (400, 422), r.text

    def test_missing_brand_rejected(self, cust):
        r = requests.post(f"{BASE}/repairs", headers=cust, json={
            "customer_type": "RETAIL", "problem_description": "TEST_Phase2 no brand",
            "charger_info": {"brand": "", "model": "M", "charger_type": "AC"},
        }, timeout=30)
        assert r.status_code == 400, r.text

    def test_missing_description_rejected(self, cust):
        r = requests.post(f"{BASE}/repairs", headers=cust, json={
            "customer_type": "RETAIL",
            "charger_info": {"brand": "TEST_B", "model": "M", "charger_type": "AC"},
        }, timeout=30)
        assert r.status_code == 422, r.text


# --- Owner "My Voltx Charger" path ---
class TestOwnerPath:
    def test_owner_chargers_listed(self, owner):
        r = requests.get(f"{BASE}/owner/chargers", headers=owner, timeout=30)
        assert r.status_code == 200, r.text
        ids = [c["charger_id"] for c in r.json()]
        assert "IND000001" in ids

    def test_owner_repair_with_charger_id(self, owner):
        r = requests.post(f"{BASE}/repairs", headers=owner, json={
            "customer_type": "STATION_OWNER", "charger_id": "IND000001",
            "problem_description": "TEST_Phase2 owner charger fault",
        }, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        created.append((d["id"], owner))
        assert d["charger_id"] == "IND000001"
        assert d["charger_info"].get("brand")


# --- Authorization: cross-customer access ---
class TestAuthorization:
    def test_other_customer_gets_403(self, cust):
        a = requests.post(f"{BASE}/repairs", headers=cust, json={
            "customer_type": "RETAIL", "problem_description": "TEST_Phase2 private",
            "charger_info": {"brand": "TEST_A", "model": "M", "charger_type": "AC"},
        }, timeout=30)
        assert a.status_code == 200
        rid = a.json()["id"]
        created.append((rid, cust))
        b = new_customer()
        g = requests.get(f"{BASE}/repairs/{rid}", headers=b, timeout=30)
        assert g.status_code == 403, g.text

    def test_unauthenticated_rejected(self):
        g = requests.get(f"{BASE}/repairs/rep_doesnotexist", timeout=30)
        assert g.status_code in (401, 403)

    def test_unknown_id_404(self, cust):
        g = requests.get(f"{BASE}/repairs/rep_nope123", headers=cust, timeout=30)
        assert g.status_code == 404


# --- Regression on pre-existing endpoints ---
class TestRegression:
    def test_wallet(self, cust):
        r = requests.get(f"{BASE}/wallet", headers=cust, timeout=30)
        assert r.status_code == 200, r.text
        assert "balance" in r.json()

    def test_stations(self, cust):
        r = requests.get(f"{BASE}/stations", headers=cust, timeout=30)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_session_flow(self, cust):
        lst = requests.get(f"{BASE}/sessions", headers=cust, timeout=30)
        assert lst.status_code == 200, lst.text
        s = requests.post(f"{BASE}/sessions/start", headers=cust,
                          json={"charger_id": "IND000001"}, timeout=30)
        assert s.status_code in (200, 400, 409), s.text
        if s.status_code == 200:
            sid = s.json()["id"]
            g = requests.get(f"{BASE}/sessions/{sid}/live", headers=cust, timeout=30)
            assert g.status_code == 200
            stop = requests.post(f"{BASE}/sessions/{sid}/stop", headers=cust, timeout=30)
            assert stop.status_code == 200, stop.text

    def test_owner_summary(self, owner):
        r = requests.get(f"{BASE}/owner/summary", headers=owner, timeout=30)
        assert r.status_code == 200, r.text

    def test_admin_summary(self, admin):
        r = requests.get(f"{BASE}/admin/summary", headers=admin, timeout=30)
        assert r.status_code == 200, r.text
