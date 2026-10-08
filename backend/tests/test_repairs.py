from auth_client import login_headers, new_phone
"""Phase 1 backend tests for the EV Charger Repair Service module.
Run: cd /app/backend && python -m pytest tests/test_repairs.py -v
Hits the live server at localhost:8001. Auth = phone OTP (demo 123456)."""
import requests
import os
import uuid

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
OTP = "123456"
OWNER_PHONE = "+919000000002"  # seeded owner of IND000001..6
ADMIN_PHONE = "+919000000001"  # seeded admin


def login(phone, name=None):
    return login_headers(BASE, phone, name)


def new_customer():
    phone = new_phone()
    return login(phone, "Repair Test"), phone


def test_create_retail_repair_unregistered():
    h, _ = new_customer()
    r = requests.post(f"{BASE}/repairs", headers=h, json={
        "customer_type": "RETAIL", "charger_info": {"brand": "Delta", "model": "AC Mini", "charger_type": "AC"},
        "problem_description": "Not powering on"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "REQUESTED"
    assert d["charger_id"] is None
    assert d["repair_request_number"].startswith("REP-")
    assert d["charger_info"]["brand"] == "Delta"
    assert "id" in d and d["id"].startswith("rep_")


def test_create_retail_missing_brand_fails():
    h, _ = new_customer()
    r = requests.post(f"{BASE}/repairs", headers=h, json={
        "customer_type": "RETAIL", "problem_description": "Broken screen"})
    assert r.status_code == 400
    assert "brand" in r.json()["detail"].lower()


def test_create_repair_for_existing_charger_retains_relationship():
    h, _ = new_customer()
    r = requests.post(f"{BASE}/repairs", headers=h, json={
        "charger_id": "IND000001", "customer_type": "RETAIL",
        "problem_description": "Connector damaged"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["charger_id"] == "IND000001"  # relationship retained, not duplicated
    assert d["charger_info"].get("brand")  # auto-filled from existing charger


def test_invalid_charger_type_rejected():
    h, _ = new_customer()
    r = requests.post(f"{BASE}/repairs", headers=h, json={
        "charger_info": {"brand": "ABB", "charger_type": "SOLAR"},
        "problem_description": "Weird noise"})
    assert r.status_code == 400


def test_missing_problem_description_rejected():
    h, _ = new_customer()
    r = requests.post(f"{BASE}/repairs", headers=h, json={"charger_info": {"brand": "ABB"}})
    assert r.status_code == 422  # pydantic required field


def test_repair_number_increments():
    h, _ = new_customer()
    a = requests.post(f"{BASE}/repairs", headers=h, json={"charger_info": {"brand": "X"}, "problem_description": "aaa"}).json()
    b = requests.post(f"{BASE}/repairs", headers=h, json={"charger_info": {"brand": "Y"}, "problem_description": "bbb"}).json()
    na = int(a["repair_request_number"].split("-")[1])
    nb = int(b["repair_request_number"].split("-")[1])
    assert nb == na + 1
    assert na >= 10001


def test_customer_cannot_access_other_customers_repair():
    h1, _ = new_customer()
    rep = requests.post(f"{BASE}/repairs", headers=h1, json={"charger_info": {"brand": "X"}, "problem_description": "abc"}).json()
    h2, _ = new_customer()
    r = requests.get(f"{BASE}/repairs/{rep['id']}", headers=h2)
    assert r.status_code == 403


def test_station_owner_can_access_repair_for_their_charger():
    h, _ = new_customer()
    rep = requests.post(f"{BASE}/repairs", headers=h, json={
        "charger_id": "IND000001", "problem_description": "owned charger issue"}).json()
    owner = login(OWNER_PHONE)
    r = requests.get(f"{BASE}/repairs/{rep['id']}", headers=owner)
    assert r.status_code == 200, r.text
    assert r.json()["id"] == rep["id"]


def test_valid_status_transition_by_customer():
    h, _ = new_customer()
    rep = requests.post(f"{BASE}/repairs", headers=h, json={"charger_info": {"brand": "X"}, "problem_description": "abc"}).json()
    r = requests.patch(f"{BASE}/repairs/{rep['id']}/status", headers=h, json={"status": "AWAITING_SHIPMENT"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "AWAITING_SHIPMENT"


def test_invalid_status_transition_rejected():
    h, _ = new_customer()
    rep = requests.post(f"{BASE}/repairs", headers=h, json={"charger_info": {"brand": "X"}, "problem_description": "abc"}).json()
    r = requests.patch(f"{BASE}/repairs/{rep['id']}/status", headers=h, json={"status": "REPAIRING"})
    assert r.status_code == 400
    assert "transition" in r.json()["detail"].lower()


def test_customer_cannot_set_admin_only_status():
    h, _ = new_customer()
    rep = requests.post(f"{BASE}/repairs", headers=h, json={"charger_info": {"brand": "X"}, "problem_description": "abc"}).json()
    requests.patch(f"{BASE}/repairs/{rep['id']}/status", headers=h, json={"status": "AWAITING_SHIPMENT"})
    requests.patch(f"{BASE}/repairs/{rep['id']}/status", headers=h, json={"status": "IN_TRANSIT_TO_VOLTX"})
    # RECEIVED_AT_VOLTX is a valid next transition but restricted to admin/repair team
    r = requests.patch(f"{BASE}/repairs/{rep['id']}/status", headers=h, json={"status": "RECEIVED_AT_VOLTX"})
    assert r.status_code == 403


def test_admin_full_flow_diagnosis_estimate_and_approval():
    cust, _ = new_customer()
    rep = requests.post(f"{BASE}/repairs", headers=cust, json={"charger_info": {"brand": "X", "charger_type": "DC"}, "problem_description": "no output"}).json()
    rid = rep["id"]
    admin = login(ADMIN_PHONE)
    # move to RECEIVED_AT_VOLTX via valid path (admin can do all)
    for s in ["AWAITING_SHIPMENT", "IN_TRANSIT_TO_VOLTX", "RECEIVED_AT_VOLTX", "DIAGNOSING"]:
        assert requests.patch(f"{BASE}/repairs/{rid}/status", headers=admin, json={"status": s}).status_code == 200
    # diagnosis with internal notes
    assert requests.patch(f"{BASE}/repairs/{rid}/diagnosis", headers=admin, json={
        "diagnosis": "PCB fault", "repairability": "REPAIRABLE", "technician_notes": "secret", "internal_notes": "order part"}).status_code == 200
    # estimate computes total
    e = requests.patch(f"{BASE}/repairs/{rid}/estimate", headers=admin, json={
        "parts": [{"name": "PCB", "qty": 1, "price": 2000}], "labor": 500, "tax": 250}).json()["estimate"]
    assert e["subtotal"] == 2500 and e["total"] == 2750
    # send estimate then customer approves
    assert requests.patch(f"{BASE}/repairs/{rid}/status", headers=admin, json={"status": "ESTIMATE_SENT"}).status_code == 200
    r = requests.patch(f"{BASE}/repairs/{rid}/status", headers=cust, json={"status": "CUSTOMER_APPROVED"})
    assert r.status_code == 200
    body = r.json()
    assert body["estimate"]["status"] == "APPROVED" and body["estimate"]["approved_at"]
    # internal diagnosis fields hidden from customer
    assert "technician_notes" not in body.get("diagnosis", {})
    assert "internal_notes" not in body.get("diagnosis", {})


def test_customer_approve_without_estimate_rejected():
    h, _ = new_customer()
    rep = requests.post(f"{BASE}/repairs", headers=h, json={"charger_info": {"brand": "X"}, "problem_description": "abc"}).json()
    admin = login(ADMIN_PHONE)
    for s in ["AWAITING_SHIPMENT", "IN_TRANSIT_TO_VOLTX", "RECEIVED_AT_VOLTX", "DIAGNOSING", "ESTIMATE_SENT"]:
        requests.patch(f"{BASE}/repairs/{rep['id']}/status", headers=admin, json={"status": s})
    # no estimate was created -> approval blocked
    r = requests.patch(f"{BASE}/repairs/{rep['id']}/status", headers=h, json={"status": "CUSTOMER_APPROVED"})
    assert r.status_code == 400
