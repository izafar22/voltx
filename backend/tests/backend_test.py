"""VoltGrid backend API tests (auth, wallet, chargers, sessions, owner, admin RBAC)."""
import os
import time
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_PHONE = "+919000000001"
OWNER_PHONE = "+919000000002"
CUSTOMER_PHONE = "+919000000003"
OTP = "123456"


def login(phone, name=None):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/request-otp", json={"phone": phone}, timeout=30)
    assert r.status_code == 200, r.text
    body = {"phone": phone, "otp": OTP}
    if name:
        body["name"] = name
    r = s.post(f"{API}/auth/verify-otp", json=body, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    s.headers.update({"Authorization": f"Bearer {data['token']}"})
    return s, data["user"]


@pytest.fixture(scope="module")
def admin():
    return login(ADMIN_PHONE)[0]


@pytest.fixture(scope="module")
def owner():
    return login(OWNER_PHONE)[0]


@pytest.fixture(scope="module")
def customer():
    return login(CUSTOMER_PHONE)[0]


# ---------------- Auth ----------------
class TestAuth:
    def test_request_otp_returns_demo_otp(self):
        r = requests.post(f"{API}/auth/request-otp", json={"phone": CUSTOMER_PHONE}, timeout=30)
        assert r.status_code == 200
        assert r.json()["demo_otp"] == OTP

    def test_verify_otp_seeded_customer(self):
        r = requests.post(f"{API}/auth/verify-otp", json={"phone": CUSTOMER_PHONE, "otp": OTP}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["token"], str) and len(d["token"]) > 10
        assert d["user"]["role"] == "customer"
        assert d["user"]["phone"] == CUSTOMER_PHONE
        assert "_id" not in d["user"]

    def test_verify_otp_new_phone_creates_customer(self):
        phone = "+9188" + uuid.uuid4().hex[:8]
        r = requests.post(f"{API}/auth/verify-otp", json={"phone": phone, "otp": OTP, "name": "TEST_New"}, timeout=30)
        assert r.status_code == 200
        u = r.json()["user"]
        assert u["role"] == "customer"
        assert u["name"] == "TEST_New"
        tok = r.json()["token"]
        w = requests.get(f"{API}/wallet", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        assert w.status_code == 200 and w.json()["balance"] == 0.0

    def test_wrong_otp_400(self):
        r = requests.post(f"{API}/auth/verify-otp", json={"phone": CUSTOMER_PHONE, "otp": "000000"}, timeout=30)
        assert r.status_code == 400

    def test_me_requires_token(self):
        assert requests.get(f"{API}/auth/me", timeout=30).status_code == 401
        assert requests.get(f"{API}/auth/me", headers={"Authorization": "Bearer bogus"}, timeout=30).status_code == 401

    def test_me_with_token(self, customer):
        r = customer.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 200
        assert r.json()["phone"] == CUSTOMER_PHONE
        assert "_id" not in r.json()

    def test_roles_of_seeded_accounts(self):
        for phone, role in [(ADMIN_PHONE, "admin"), (OWNER_PHONE, "owner")]:
            _, u = login(phone)
            assert u["role"] == role


# ---------------- Wallet + charger lookup ----------------
class TestWalletAndLookup:
    def test_wallet_balance_and_topup(self, customer):
        before = customer.get(f"{API}/wallet", timeout=30)
        assert before.status_code == 200
        b0 = before.json()["balance"]
        r = customer.post(f"{API}/wallet/topup", json={"amount": 250}, timeout=30)
        assert r.status_code == 200
        assert r.json()["balance"] == round(b0 + 250, 2)
        # persistence
        assert customer.get(f"{API}/wallet", timeout=30).json()["balance"] == round(b0 + 250, 2)
        txns = customer.get(f"{API}/wallet/transactions", timeout=30)
        assert txns.status_code == 200
        top = txns.json()[0]
        assert top["type"] == "topup" and top["amount"] == 250
        ntf = customer.get(f"{API}/notifications", timeout=30)
        assert ntf.status_code == 200
        assert any(n["type"] == "payment_successful" for n in ntf.json())

    def test_topup_invalid_amount(self, customer):
        assert customer.post(f"{API}/wallet/topup", json={"amount": -5}, timeout=30).status_code == 400

    def test_wallet_requires_auth(self):
        assert requests.get(f"{API}/wallet", timeout=30).status_code == 401

    def test_charger_lookup(self, customer):
        r = customer.get(f"{API}/chargers/IND000001", timeout=30)
        assert r.status_code == 200
        c = r.json()
        assert c["charger_id"] == "IND000001"
        assert c["price_per_kwh"] > 0
        assert c["owner_name"]
        assert "_id" not in c

    def test_charger_lookup_unknown_404(self, customer):
        assert customer.get(f"{API}/chargers/IND999999", timeout=30).status_code == 404


# ---------------- Session lifecycle (uses IND000001) ----------------
class TestSessionLifecycle:
    def test_full_lifecycle(self, customer, owner):
        # ensure no active session
        for s in customer.get(f"{API}/sessions", timeout=30).json():
            if s["status"] == "active":
                customer.post(f"{API}/sessions/{s['session_id']}/stop", timeout=30)
        # ensure balance
        bal = customer.get(f"{API}/wallet", timeout=30).json()["balance"]
        if bal < 500:
            customer.post(f"{API}/wallet/topup", json={"amount": 1000}, timeout=30)
            bal = customer.get(f"{API}/wallet", timeout=30).json()["balance"]

        owner_before = owner.get(f"{API}/owner/summary", timeout=30).json()

        r = customer.post(f"{API}/sessions/start", json={"charger_id": "IND000001"}, timeout=30)
        assert r.status_code == 200, r.text
        sess = r.json()
        sid = sess["session_id"]
        assert sess["status"] == "active"

        # charger becomes Charging
        assert customer.get(f"{API}/chargers/IND000001", timeout=30).json()["status"] == "Charging"
        # second session blocked
        r2 = customer.post(f"{API}/sessions/start", json={"charger_id": "IND000002"}, timeout=30)
        assert r2.status_code == 400
        assert "active session" in r2.json()["detail"].lower()

        l1 = customer.get(f"{API}/sessions/{sid}/live", timeout=30)
        assert l1.status_code == 200
        live1 = l1.json()["live"]
        for k in ("soc", "energy_kwh", "power_kw", "cost", "voltage", "current", "elapsed_seconds"):
            assert k in live1
        time.sleep(4)
        live2 = customer.get(f"{API}/sessions/{sid}/live", timeout=30).json()["live"]
        assert live2["energy_kwh"] > live1["energy_kwh"], (live1, live2)
        assert live2["cost"] >= live1["cost"]

        st = customer.post(f"{API}/sessions/{sid}/stop", timeout=30)
        assert st.status_code == 200, st.text
        fin = st.json()
        assert fin["energy_kwh"] > 0 and fin["cost"] > 0
        assert fin["owner_amount"] == round(fin["cost"] * 0.9, 2)
        assert fin["company_amount"] == round(fin["cost"] * 0.1, 2)
        assert abs(fin["balance"] - round(bal - fin["cost"], 2)) < 0.05

        # double stop
        assert customer.post(f"{API}/sessions/{sid}/stop", timeout=30).status_code == 400
        # charger released
        assert customer.get(f"{API}/chargers/IND000001", timeout=30).json()["status"] == "Available"
        # history
        hist = customer.get(f"{API}/sessions", timeout=30).json()
        done = [s for s in hist if s["session_id"] == sid][0]
        assert done["status"] == "completed" and done["cost"] == fin["cost"]
        # notification
        assert any(n["type"] == "charging_stopped" for n in customer.get(f"{API}/notifications", timeout=30).json())
        # owner credited 90%
        owner_after = owner.get(f"{API}/owner/summary", timeout=30).json()
        assert round(owner_after["wallet"] - owner_before["wallet"], 2) == fin["owner_amount"]
        assert owner_after["today_earnings"] >= fin["owner_amount"]
        assert owner_after["units_sold"] >= fin["energy_kwh"]

    def test_start_on_offline_charger(self, customer):
        r = customer.post(f"{API}/sessions/start", json={"charger_id": "IND000005"}, timeout=30)
        assert r.status_code == 400

    def test_start_unknown_charger_404(self, customer):
        assert customer.post(f"{API}/sessions/start", json={"charger_id": "INDXXXX"}, timeout=30).status_code == 404

    def test_min_balance_enforced(self):
        phone = "+9177" + uuid.uuid4().hex[:8]
        s, _ = login(phone, name="TEST_LowBal")
        s.post(f"{API}/wallet/topup", json={"amount": 50}, timeout=30)
        r = s.post(f"{API}/sessions/start", json={"charger_id": "IND000002"}, timeout=30)
        assert r.status_code == 400
        assert "balance" in r.json()["detail"].lower()

    def test_live_other_users_session_404(self, customer):
        phone = "+9166" + uuid.uuid4().hex[:8]
        other, _ = login(phone, name="TEST_Other")
        sessions = customer.get(f"{API}/sessions", timeout=30).json()
        if not sessions:
            pytest.skip("no sessions to check")
        sid = sessions[0]["session_id"]
        assert other.get(f"{API}/sessions/{sid}/live", timeout=30).status_code == 404


# ---------------- Owner ----------------
class TestOwner:
    def test_owner_chargers_telemetry(self, owner):
        r = owner.get(f"{API}/owner/chargers", timeout=30)
        assert r.status_code == 200
        chargers = r.json()
        assert len(chargers) >= 6
        c = chargers[0]
        for k in ("charger_id", "voltage", "power_kw", "temperature", "signal", "firmware", "last_heartbeat", "online"):
            assert k in c

    def test_owner_transactions(self, owner):
        r = owner.get(f"{API}/owner/transactions", timeout=30)
        assert r.status_code == 200 and isinstance(r.json(), list)

    def test_withdraw_and_reject_refund(self, owner, admin):
        summary = owner.get(f"{API}/owner/summary", timeout=30).json()
        bal = summary["wallet"]
        if bal < 10:
            pytest.skip("owner wallet empty; run session lifecycle first")
        amt = round(min(10.0, bal), 2)
        r = owner.post(f"{API}/owner/withdraw", json={"amount": amt}, timeout=30)
        assert r.status_code == 200, r.text
        wd = r.json()["withdrawal"]
        assert wd["status"] == "requested" and wd["amount"] == amt
        after = owner.get(f"{API}/owner/summary", timeout=30).json()["wallet"]
        assert round(bal - after, 2) == amt
        wds = owner.get(f"{API}/owner/withdrawals", timeout=30)
        assert wds.status_code == 200
        assert any(w["id"] == wd["id"] for w in wds.json())
        # admin rejects -> refund
        rej = admin.patch(f"{API}/admin/withdrawals/{wd['id']}", json={"status": "rejected"}, timeout=30)
        assert rej.status_code == 200
        refunded = owner.get(f"{API}/owner/summary", timeout=30).json()["wallet"]
        assert round(refunded, 2) == round(bal, 2)
        assert [w for w in admin.get(f"{API}/admin/withdrawals", timeout=30).json() if w["id"] == wd["id"]][0]["status"] == "rejected"

    def test_withdraw_over_balance_400(self, owner):
        assert owner.post(f"{API}/owner/withdraw", json={"amount": 10 ** 9}, timeout=30).status_code == 400

    def test_withdraw_invalid_status_patch(self, admin):
        wds = admin.get(f"{API}/admin/withdrawals", timeout=30).json()
        if not wds:
            pytest.skip("no withdrawals")
        assert admin.patch(f"{API}/admin/withdrawals/{wds[0]['id']}", json={"status": "bogus"}, timeout=30).status_code == 400

    def test_withdraw_unknown_id_404(self, admin):
        assert admin.patch(f"{API}/admin/withdrawals/wd_none", json={"status": "completed"}, timeout=30).status_code == 404


# ---------------- RBAC ----------------
class TestRBAC:
    ADMIN_ROUTES = ["/admin/summary", "/admin/chargers", "/admin/owners", "/admin/users", "/admin/faults", "/admin/withdrawals", "/admin/sessions"]

    def test_customer_forbidden_on_admin(self, customer):
        for route in self.ADMIN_ROUTES:
            assert customer.get(f"{API}{route}", timeout=30).status_code == 403, route

    def test_customer_forbidden_on_owner(self, customer):
        for route in ["/owner/summary", "/owner/chargers", "/owner/transactions", "/owner/withdrawals"]:
            assert customer.get(f"{API}{route}", timeout=30).status_code == 403, route

    def test_owner_forbidden_on_admin_allowed_on_owner(self, owner):
        assert owner.get(f"{API}/admin/summary", timeout=30).status_code == 403
        assert owner.get(f"{API}/owner/summary", timeout=30).status_code == 200

    def test_admin_routes_unauthenticated(self):
        assert requests.get(f"{API}/admin/summary", timeout=30).status_code == 401


# ---------------- Admin ----------------
class TestAdmin:
    def test_admin_summary(self, admin):
        r = admin.get(f"{API}/admin/summary", timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("total_revenue", "commission", "owner_payouts", "online", "offline", "faults", "customers", "owners", "chargers_total"):
            assert k in d
        assert abs(d["commission"] - round(d["total_revenue"] * 0.1, 2)) <= 0.5
        assert abs(d["owner_payouts"] - round(d["total_revenue"] * 0.9, 2)) <= 0.5
        assert d["customers"] >= 1 and d["owners"] >= 1

    def test_admin_chargers_telemetry(self, admin):
        r = admin.get(f"{API}/admin/chargers", timeout=30)
        assert r.status_code == 200
        c = r.json()[0]
        for k in ("voltage", "current", "power_kw", "temperature", "signal", "firmware", "last_heartbeat", "owner_name"):
            assert k in c

    def test_status_change_and_restart(self, admin):
        cid = "IND000004"
        assert admin.post(f"{API}/admin/chargers/{cid}/status", json={"status": "Fault"}, timeout=30).status_code == 200
        got = [c for c in admin.get(f"{API}/admin/chargers", timeout=30).json() if c["charger_id"] == cid][0]
        assert got["status"] == "Fault"
        faults = admin.get(f"{API}/admin/faults", timeout=30).json()
        assert any(f["charger_id"] == cid for f in faults)
        assert admin.post(f"{API}/admin/chargers/{cid}/status", json={"status": "Offline"}, timeout=30).status_code == 200
        got = [c for c in admin.get(f"{API}/admin/chargers", timeout=30).json() if c["charger_id"] == cid][0]
        assert got["status"] == "Offline" and got["online"] is False
        assert admin.post(f"{API}/admin/chargers/{cid}/restart", timeout=30).status_code == 200
        got = [c for c in admin.get(f"{API}/admin/chargers", timeout=30).json() if c["charger_id"] == cid][0]
        assert got["status"] == "Available" and got["online"] is True
        assert any(f["message"].startswith("Remote restart") and f["charger_id"] == cid
                   for f in admin.get(f"{API}/admin/faults", timeout=30).json())

    def test_invalid_status_400(self, admin):
        assert admin.post(f"{API}/admin/chargers/IND000004/status", json={"status": "Nope"}, timeout=30).status_code == 400

    def test_restart_unknown_charger_404(self, admin):
        assert admin.post(f"{API}/admin/chargers/IND999999/restart", timeout=30).status_code == 404

    def test_create_owner_and_charger(self, admin):
        phone = "+9155" + uuid.uuid4().hex[:8]
        r = admin.post(f"{API}/admin/owners", json={"name": "TEST_Owner", "phone": phone}, timeout=30)
        assert r.status_code == 200, r.text
        o = r.json()["owner"]
        assert o["role"] == "owner"
        assert any(x["user_id"] == o["user_id"] for x in admin.get(f"{API}/admin/owners", timeout=30).json())
        # dup phone
        assert admin.post(f"{API}/admin/owners", json={"name": "TEST_Dup", "phone": phone}, timeout=30).status_code == 400
        # charger
        cr = admin.post(f"{API}/admin/chargers", json={
            "name": "TEST_Charger", "owner_id": o["user_id"], "connector": "CCS2",
            "price_per_kwh": 20.0, "max_power_kw": 30.0, "location": "TEST City"}, timeout=30)
        assert cr.status_code == 200, cr.text
        ch = cr.json()["charger"]
        assert ch["charger_id"].startswith("IND") and len(ch["charger_id"]) == 9
        assert ch["status"] == "Available"
        listed = [c for c in admin.get(f"{API}/admin/chargers", timeout=30).json() if c["charger_id"] == ch["charger_id"]]
        assert listed and listed[0]["owner_name"] == "TEST_Owner"

    def test_admin_users_and_wallet_adjust(self, admin, customer):
        users = admin.get(f"{API}/admin/users", timeout=30)
        assert users.status_code == 200
        target = [u for u in users.json() if u["phone"] == CUSTOMER_PHONE]
        assert target, "seeded customer missing from /admin/users"
        uid = target[0]["user_id"]
        before = target[0]["wallet"]
        r = admin.post(f"{API}/admin/wallet/adjust", json={"user_id": uid, "amount": 25, "note": "TEST_adjust"}, timeout=30)
        assert r.status_code == 200
        assert r.json()["balance"] == round(before + 25, 2)
        assert customer.get(f"{API}/wallet", timeout=30).json()["balance"] == round(before + 25, 2)
        # revert
        admin.post(f"{API}/admin/wallet/adjust", json={"user_id": uid, "amount": -25, "note": "TEST_revert"}, timeout=30)

    def test_admin_sessions_list(self, admin):
        r = admin.get(f"{API}/admin/sessions", timeout=30)
        assert r.status_code == 200 and isinstance(r.json(), list)
