"""RUSHX backend API regression tests (public, auth, customer, admin)."""
import uuid

import pytest

from conftest import BASE_URL


# ---------------- Public: products & AMC plans ----------------
class TestPublicCatalog:
    def test_root(self, api):
        r = api.get(f"{BASE_URL}/api/")
        assert r.status_code == 200
        assert r.json().get("message") == "RUSHX API"

    def test_products_list(self, api):
        r = api.get(f"{BASE_URL}/api/products")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 6, f"expected 6 seeded products, got {len(data)}"
        slugs = {p["slug"] for p in data}
        assert "home-7kw" in slugs and "powerboy-powerwall" in slugs
        for p in data:
            assert "_id" not in p
            for k in ("name", "category", "power", "image", "description", "specs"):
                assert k in p and p[k] not in (None, "")

    def test_product_detail(self, api):
        r = api.get(f"{BASE_URL}/api/products/home-7kw")
        assert r.status_code == 200
        p = r.json()
        assert p["slug"] == "home-7kw"
        assert p["name"] == "RUSHX Home 7.4kW"
        assert isinstance(p["specs"], list) and len(p["specs"]) > 0

    def test_product_detail_not_found(self, api):
        r = api.get(f"{BASE_URL}/api/products/does-not-exist")
        assert r.status_code == 404

    def test_amc_plans_sorted(self, api):
        r = api.get(f"{BASE_URL}/api/amc-plans")
        assert r.status_code == 200
        plans = r.json()
        assert len(plans) == 3
        assert [p["id"] for p in plans] == ["plan_basic", "plan_standard", "plan_premium"]
        assert [p["price"] for p in plans] == [4999, 9999, 18999]
        assert [p["order"] for p in plans] == [1, 2, 3]


# ---------------- Leads (mocked WhatsApp) ----------------
class TestLeads:
    def test_create_lead_and_whatsapp_log(self, api, admin_client, mongo_db):
        payload = {
            "name": "TEST Lead", "email": "TEST_lead@example.com", "phone": "9999900001",
            "company": "TEST Co", "segment": "Commercial", "product": "RUSHX Home 7.4kW",
            "message": "TEST enquiry", "source": "website",
        }
        r = api.post(f"{BASE_URL}/api/leads", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["whatsapp_sent"] is True
        lead_id = body["lead_id"]
        assert lead_id.startswith("lead_")

        # verify persisted with status New via admin list
        leads = admin_client.get(f"{BASE_URL}/api/admin/leads").json()
        match = [l for l in leads if l["id"] == lead_id]
        assert match, "created lead not returned by /api/admin/leads"
        assert match[0]["status"] == "New"
        assert match[0]["name"] == "TEST Lead"

        # verify mocked whatsapp message logged
        msgs = admin_client.get(f"{BASE_URL}/api/admin/messages").json()
        refs = [m for m in msgs if m.get("ref") == lead_id]
        assert refs, "no WhatsApp message logged for lead"
        assert refs[0]["channel"] == "whatsapp"
        assert refs[0]["to"] == payload["phone"]

        mongo_db.leads.delete_many({"id": lead_id})
        mongo_db.messages.delete_many({"ref": lead_id})

    def test_create_lead_invalid_email(self, api):
        r = api.post(f"{BASE_URL}/api/leads", json={
            "name": "x", "email": "not-an-email", "phone": "1", "message": "m"})
        assert r.status_code == 422

    def test_create_lead_missing_fields(self, api):
        r = api.post(f"{BASE_URL}/api/leads", json={"name": "x"})
        assert r.status_code == 422


# ---------------- Auth ----------------
class TestAuth:
    def test_me_unauthenticated(self, api):
        r = api.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401

    def test_me_invalid_token(self, api):
        r = api.get(f"{BASE_URL}/api/auth/me",
                    headers={"Authorization": "Bearer totally-invalid"})
        assert r.status_code == 401

    def test_me_with_session(self, cust_client, customer_session):
        r = cust_client.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200, r.text
        u = r.json()
        assert u["user_id"] == customer_session["user_id"]
        assert u["email"] == customer_session["email"]
        assert u["role"] == "customer"

    def test_admin_me_role(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_session_create_missing_header(self, api):
        r = api.post(f"{BASE_URL}/api/auth/session")
        assert r.status_code == 400

    def test_session_create_invalid_id(self, api):
        r = api.post(f"{BASE_URL}/api/auth/session",
                     headers={"X-Session-ID": "invalid-session-id"})
        assert r.status_code == 401


# ---------------- Bookings ----------------
class TestBookings:
    def test_bookings_require_auth(self, api):
        assert api.get(f"{BASE_URL}/api/bookings").status_code == 401
        assert api.post(f"{BASE_URL}/api/bookings", json={
            "service_type": "Installation", "date": "2026-08-01",
            "slot": "10:00 AM", "description": "d"}).status_code == 401

    def test_create_and_list_booking(self, cust_client, admin_client, customer_session):
        payload = {"service_type": "Installation", "date": "2026-08-01",
                   "slot": "10:00 AM - 12:00 PM", "device": "RUSHX Home 7.4kW",
                   "description": "TEST booking"}
        r = cust_client.post(f"{BASE_URL}/api/bookings", json=payload)
        assert r.status_code == 200, r.text
        bk = r.json()["booking"]
        assert bk["status"] == "Requested"
        assert bk["technician"] == ""
        assert bk["user_id"] == customer_session["user_id"]
        assert "_id" not in bk
        pytest.booking_id = bk["id"]

        mine = cust_client.get(f"{BASE_URL}/api/bookings")
        assert mine.status_code == 200
        rows = mine.json()
        assert all(b["user_id"] == customer_session["user_id"] for b in rows)
        assert any(b["id"] == bk["id"] for b in rows)

        msgs = admin_client.get(f"{BASE_URL}/api/admin/messages").json()
        assert any(m.get("ref") == bk["id"] for m in msgs), "booking WhatsApp not logged"

    def test_admin_assign_technician(self, admin_client, cust_client):
        bid = getattr(pytest, "booking_id", None)
        assert bid, "booking not created in previous test"
        r = admin_client.patch(f"{BASE_URL}/api/admin/bookings/{bid}",
                               json={"status": "Scheduled", "technician": "TEST Tech"})
        assert r.status_code == 200
        rows = cust_client.get(f"{BASE_URL}/api/bookings").json()
        row = [b for b in rows if b["id"] == bid][0]
        assert row["status"] == "Scheduled"
        assert row["technician"] == "TEST Tech"

    def test_customer_isolation(self, cust_client, mongo_db, customer_session):
        """Another user's bookings must not appear."""
        other_uid = "TEST_other_" + uuid.uuid4().hex[:8]
        mongo_db.bookings.insert_one({
            "id": "TEST_bk_other", "user_id": other_uid, "service_type": "Repair",
            "date": "2026-08-02", "slot": "x", "description": "other", "status": "Requested",
            "technician": "", "created_at": "2026-01-01T00:00:00+00:00"})
        rows = cust_client.get(f"{BASE_URL}/api/bookings").json()
        assert not any(b["id"] == "TEST_bk_other" for b in rows)
        mongo_db.bookings.delete_many({"id": "TEST_bk_other"})


# ---------------- Subscriptions / invoices (Razorpay mocked) ----------------
class TestSubscriptions:
    def test_subscribe_invalid_plan(self, cust_client):
        r = cust_client.post(f"{BASE_URL}/api/subscriptions", json={"plan_id": "nope"})
        assert r.status_code == 404

    def test_subscribe_requires_auth(self, api):
        r = api.post(f"{BASE_URL}/api/subscriptions", json={"plan_id": "plan_basic"})
        assert r.status_code == 401

    def test_subscribe_creates_sub_invoice_message(self, cust_client, admin_client):
        r = cust_client.post(f"{BASE_URL}/api/subscriptions", json={"plan_id": "plan_standard"})
        assert r.status_code == 200, r.text
        sub = r.json()["subscription"]
        assert sub["status"] == "active"
        assert sub["plan_name"] == "Standard"
        assert sub["amount"] == 9999
        assert sub["razorpay_subscription_id"].startswith("MOCK_")

        me = cust_client.get(f"{BASE_URL}/api/subscriptions/me")
        assert me.status_code == 200
        assert me.json()["id"] == sub["id"]

        inv = cust_client.get(f"{BASE_URL}/api/invoices")
        assert inv.status_code == 200
        invoices = inv.json()
        rows = [i for i in invoices if i["subscription_id"] == sub["id"]]
        assert rows, "no invoice created for subscription"
        assert rows[0]["status"] == "paid"
        assert rows[0]["amount"] == 9999

        msgs = admin_client.get(f"{BASE_URL}/api/admin/messages").json()
        assert any(m.get("ref") == sub["id"] for m in msgs), "welcome WhatsApp not logged"

        adm = admin_client.get(f"{BASE_URL}/api/admin/subscriptions").json()
        assert any(s["id"] == sub["id"] for s in adm)

    def test_resubscribe_cancels_previous(self, cust_client, mongo_db, customer_session):
        r = cust_client.post(f"{BASE_URL}/api/subscriptions", json={"plan_id": "plan_premium"})
        assert r.status_code == 200
        active = list(mongo_db.subscriptions.find(
            {"user_id": customer_session["user_id"], "status": "active"}))
        assert len(active) == 1, f"expected single active sub, got {len(active)}"
        assert active[0]["plan_id"] == "plan_premium"

    def test_cancel_subscription(self, cust_client):
        r = cust_client.post(f"{BASE_URL}/api/subscriptions/cancel")
        assert r.status_code == 200
        me = cust_client.get(f"{BASE_URL}/api/subscriptions/me")
        assert me.status_code == 200
        assert me.json() == {}


# ---------------- Quotes ----------------
class TestQuotes:
    def test_quotes_require_auth(self, api):
        assert api.get(f"{BASE_URL}/api/quotes").status_code == 401

    def test_admin_creates_quote_visible_to_customer(self, admin_client, cust_client, customer_session):
        r = admin_client.post(f"{BASE_URL}/api/admin/quotes", json={
            "user_id": customer_session["user_id"], "lead_id": "",
            "title": "TEST Quote", "amount": 55000.0, "details": "TEST details"})
        assert r.status_code == 200, r.text
        q = r.json()["quote"]
        assert q["status"] == "pending"
        assert "_id" not in q
        pytest.quote_id = q["id"]

        rows = cust_client.get(f"{BASE_URL}/api/quotes").json()
        mine = [x for x in rows if x["id"] == q["id"]]
        assert mine, "quote not visible to customer"
        assert mine[0]["amount"] == 55000.0

    def test_customer_approves_quote(self, cust_client):
        qid = getattr(pytest, "quote_id", None)
        assert qid
        r = cust_client.patch(f"{BASE_URL}/api/quotes/{qid}", json={"decision": "approved"})
        assert r.status_code == 200
        rows = cust_client.get(f"{BASE_URL}/api/quotes").json()
        assert [x for x in rows if x["id"] == qid][0]["status"] == "approved"

    def test_decline_flow_and_unknown_quote(self, cust_client, admin_client, customer_session):
        r = admin_client.post(f"{BASE_URL}/api/admin/quotes", json={
            "user_id": customer_session["user_id"], "title": "TEST Quote 2",
            "amount": 1000.0, "details": "d"})
        qid = r.json()["quote"]["id"]
        assert cust_client.patch(f"{BASE_URL}/api/quotes/{qid}",
                                 json={"decision": "declined"}).status_code == 200
        rows = cust_client.get(f"{BASE_URL}/api/quotes").json()
        assert [x for x in rows if x["id"] == qid][0]["status"] == "declined"
        assert cust_client.patch(f"{BASE_URL}/api/quotes/nope",
                                 json={"decision": "approved"}).status_code == 404

    def test_quote_of_other_user_not_updatable(self, cust_client, mongo_db):
        mongo_db.quotes.insert_one({"id": "TEST_qt_other", "user_id": "TEST_someone_else",
                                    "title": "t", "amount": 1, "details": "d",
                                    "status": "pending", "created_at": "2026-01-01T00:00:00+00:00"})
        r = cust_client.patch(f"{BASE_URL}/api/quotes/TEST_qt_other", json={"decision": "approved"})
        assert r.status_code == 404
        mongo_db.quotes.delete_many({"id": "TEST_qt_other"})


# ---------------- Admin RBAC & overview ----------------
ADMIN_GET_ROUTES = ["/api/admin/stats", "/api/admin/leads", "/api/admin/bookings",
                    "/api/admin/subscriptions", "/api/admin/customers", "/api/admin/messages"]


class TestAdmin:
    @pytest.mark.parametrize("route", ADMIN_GET_ROUTES)
    def test_admin_routes_ok(self, admin_client, route):
        r = admin_client.get(f"{BASE_URL}{route}")
        assert r.status_code == 200, f"{route} -> {r.status_code} {r.text[:200]}"
        data = r.json()
        assert isinstance(data, (list, dict))

    @pytest.mark.parametrize("route", ADMIN_GET_ROUTES)
    def test_admin_routes_forbidden_for_customer(self, cust_client, route):
        r = cust_client.get(f"{BASE_URL}{route}")
        assert r.status_code == 403, f"{route} -> {r.status_code}"

    @pytest.mark.parametrize("route", ADMIN_GET_ROUTES)
    def test_admin_routes_unauthenticated(self, api, route):
        assert api.get(f"{BASE_URL}{route}").status_code == 401

    def test_admin_write_routes_forbidden_for_customer(self, cust_client):
        assert cust_client.patch(f"{BASE_URL}/api/admin/leads/x",
                                 json={"status": "Won"}).status_code == 403
        assert cust_client.patch(f"{BASE_URL}/api/admin/bookings/x",
                                 json={"status": "Done"}).status_code == 403
        assert cust_client.post(f"{BASE_URL}/api/admin/quotes", json={
            "user_id": "x", "title": "t", "amount": 1, "details": "d"}).status_code == 403

    def test_stats_shape(self, admin_client):
        s = admin_client.get(f"{BASE_URL}/api/admin/stats").json()
        for k in ("leads", "new_leads", "customers", "bookings",
                  "active_subscriptions", "revenue"):
            assert k in s, f"missing stat {k}"
            assert isinstance(s[k], (int, float))

    def test_update_lead_status(self, api, admin_client, mongo_db):
        lead_id = api.post(f"{BASE_URL}/api/leads", json={
            "name": "TEST Status", "email": "TEST_s@example.com", "phone": "9000000002",
            "message": "m"}).json()["lead_id"]
        r = admin_client.patch(f"{BASE_URL}/api/admin/leads/{lead_id}", json={"status": "Won"})
        assert r.status_code == 200
        leads = admin_client.get(f"{BASE_URL}/api/admin/leads").json()
        assert [l for l in leads if l["id"] == lead_id][0]["status"] == "Won"
        mongo_db.leads.delete_many({"id": lead_id})
        mongo_db.messages.delete_many({"ref": lead_id})

    def test_customers_list_excludes_admin(self, admin_client):
        rows = admin_client.get(f"{BASE_URL}/api/admin/customers").json()
        assert all(c["role"] == "customer" for c in rows)
        assert all("_id" not in c for c in rows)
