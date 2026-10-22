if __package__:
    from .services.whatsapp_service import Settings as WhatsAppSettings, consent_record, event_for, webhook_router, WebhookAccessLogFilter, WhatsAppService
    from .services.repair_facts import validate_transition_facts, calculated_estimate, money, text_fact, exact_money_input, MONEY_FIELDS
    from .services.safety_indexes import initialize_safety_indexes
    from .services.payment_repository import MongoPaymentRepository
    from .services.payment_config import public_payment_instructions
    from .services.whatsapp_service import payment_received_notification
    from .services.payment_service import PaymentService, ManualPaymentProcessor
    from .demo_chargers import seed_demo_chargers
    from .auth_service import AuthService, AuthSettings, auth_router, normalize_phone
else:
    from services.whatsapp_service import Settings as WhatsAppSettings, consent_record, event_for, webhook_router, WebhookAccessLogFilter, WhatsAppService
    from services.repair_facts import validate_transition_facts, calculated_estimate, money, text_fact, exact_money_input, MONEY_FIELDS
    from services.safety_indexes import initialize_safety_indexes
    from services.payment_repository import MongoPaymentRepository
    from services.payment_config import public_payment_instructions
    from services.whatsapp_service import payment_received_notification
    from services.payment_service import PaymentService, ManualPaymentProcessor
    from demo_chargers import seed_demo_chargers
    from auth_service import AuthService, AuthSettings, auth_router, normalize_phone

from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends, Response, Query
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import math
import hashlib
import json
import base64
from pymongo.errors import DuplicateKeyError
from decimal import Decimal
import random
from pymongo import ReturnDocument
from pydantic import BaseModel, Field, StrictBool, field_validator
from typing import Optional, List, Literal
from datetime import datetime, timezone, timedelta

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

JWT_SECRET = os.environ['JWT_SECRET']
auth_settings = AuthSettings.from_env()
auth_service = AuthService(db, auth_settings)
MIN_START_BALANCE = 100.0
OWNER_SHARE = 0.90
COMPANY_SHARE = 0.10
BATTERY_CAPACITY_KWH = 40.0  # assumed EV battery for SoC simulation
SIM_SPEED = 120  # demo time acceleration: 1 real second = 2 simulated minutes

ADMIN_EMAIL = "crazycoder4192@gmail.com"


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt=None):
    return (dt or now_utc()).isoformat()


def nid(p):
    return f"{p}_{uuid.uuid4().hex[:12]}"


def parse_dt(v):
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v


# ---------------- Models ----------------
class TopupBody(BaseModel):
    amount: float = Field(..., le=99999999.99, allow_inf_nan=False)


class StartBody(BaseModel):
    charger_id: str


class ChargerCreate(BaseModel):
    name: str
    owner_id: str
    connector: str = "Type 2"
    price_per_kwh: float = 15.0
    max_power_kw: float = 7.4
    location: str = ""


class OwnerCreate(BaseModel):
    name: str
    phone: str


class WithdrawBody(BaseModel):
    amount: float


class WalletAdjust(BaseModel):
    user_id: str
    amount: float
    note: Optional[str] = "Admin adjustment"


# ---------------- Auth helpers ----------------
async def get_current_user(request: Request):
    return await auth_service.authenticate(request)


def require(*roles):
    async def dep(user=Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return dep


async def get_balance(user_id):
    w = await db.wallets.find_one({"user_id": user_id}, {"_id": 0})
    return w["balance"] if w else 0.0


async def add_wallet_txn(user_id, txn_type, amount, note=""):
    w = await db.wallets.find_one({"user_id": user_id})
    bal = (w["balance"] if w else 0.0) + amount
    await db.wallets.update_one({"user_id": user_id}, {"$set": {"balance": round(bal, 2)}}, upsert=True)
    await db.transactions.insert_one({
        "id": nid("txn"), "user_id": user_id, "type": txn_type, "amount": round(amount, 2),
        "balance_after": round(bal, 2), "note": note, "created_at": iso(),
    })
    return round(bal, 2)


async def add_owner_earning(owner_id, amount, note=""):
    w = await db.owner_wallets.find_one({"user_id": owner_id})
    bal = (w["balance"] if w else 0.0) + amount
    await db.owner_wallets.update_one({"user_id": owner_id}, {"$set": {"balance": round(bal, 2)}}, upsert=True)
    await db.owner_transactions.insert_one({
        "id": nid("otxn"), "owner_id": owner_id, "type": "earning" if amount >= 0 else "withdrawal",
        "amount": round(amount, 2), "balance_after": round(bal, 2), "note": note, "created_at": iso(),
    })
    return round(bal, 2)


async def notify(user_id, ntype, message):
    await db.notifications.insert_one({
        "id": nid("ntf"), "user_id": user_id, "type": ntype, "message": message,
        "read": False, "created_at": iso(),
    })


# ---------------- Live session computation ----------------
def compute_live(session, charger, max_cost=None):
    start = parse_dt(session["start_time"])
    end = parse_dt(session["end_time"]) if session.get("end_time") else now_utc()
    elapsed_s = max(0, (end - start).total_seconds()) * SIM_SPEED
    power = charger["max_power_kw"]
    price = session["price_per_kwh"]
    energy = round(power * (elapsed_s / 3600.0), 3)
    capped = False
    max_energy = BATTERY_CAPACITY_KWH * 0.8  # charge session tops up ~80%
    if energy > max_energy:
        energy = round(max_energy, 3)
        capped = True
    if max_cost is not None and energy * price > max_cost:
        energy = round(max_cost / price, 3) if price else 0
        capped = True  # wallet exhausted -> stop accruing
    cost = round(energy * price, 2)
    soc = min(100, round(20 + (energy / BATTERY_CAPACITY_KWH) * 100))
    charging = session["status"] == "active" and soc < 100 and not capped
    return {
        "elapsed_seconds": int(elapsed_s),
        "energy_kwh": energy,
        "power_kw": power if charging else 0,
        "cost": cost,
        "soc": soc,
        "capped": capped,
        "voltage": 230 + random.randint(-3, 3) if session["status"] == "active" else 0,
        "current": round((power * 1000) / 230, 1) if charging else 0,
    }


# ---------------- Auth routes ----------------
api_router.include_router(auth_router(auth_service))


def require_demo_finance():
    if auth_settings.environment not in ("development", "test"):
        raise HTTPException(403, "Demo financial operations are disabled outside development and test")


# ---------------- Wallet (customer) ----------------
@api_router.get("/wallet")
async def wallet(user=Depends(get_current_user)):
    return {"balance": await get_balance(user["user_id"])}


@api_router.post("/wallet/topup")
async def topup(body: TopupBody, user=Depends(get_current_user)):
    require_demo_finance()
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    bal = await add_wallet_txn(user["user_id"], "topup", body.amount, "Wallet top-up")  # MOCKED payment
    await notify(user["user_id"], "payment_successful", f"₹{body.amount:.0f} added to your wallet.")
    return {"ok": True, "balance": bal}


@api_router.get("/wallet/transactions")
async def wallet_txns(user=Depends(get_current_user)):
    return await db.transactions.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


# ---------------- Chargers ----------------
async def charger_public(c):
    owner = await db.users.find_one({"user_id": c["owner_id"]}, {"_id": 0, "name": 1})
    return {
        "charger_id": c["charger_id"], "name": c["name"], "status": c["status"],
        "price_per_kwh": c["price_per_kwh"], "connector": c["connector"],
        "max_power_kw": c["max_power_kw"], "location": c.get("location", ""),
        "owner_name": owner["name"] if owner else "—", "online": c.get("online", True),
        "lat": c.get("lat"), "lng": c.get("lng"),
    }


@api_router.get("/stations")
async def list_stations(user=Depends(get_current_user)):
    chargers = await db.chargers.find({}, {"_id": 0}).sort("charger_id", 1).to_list(500)
    return [await charger_public(c) for c in chargers]


@api_router.get("/chargers/{charger_id}")
async def get_charger(charger_id: str, user=Depends(get_current_user)):
    c = await db.chargers.find_one({"charger_id": charger_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Charger not found")
    return await charger_public(c)


# ---------------- Charging sessions ----------------
@api_router.post("/sessions/start")
async def start_session(body: StartBody, user=Depends(get_current_user)):
    require_demo_finance()
    c = await db.chargers.find_one({"charger_id": body.charger_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Charger not found")
    if not c.get("online", True) or c["status"] in ("Offline", "Fault"):
        raise HTTPException(status_code=400, detail=f"Charger is {c['status'].lower()}")
    if c["status"] != "Available":
        raise HTTPException(status_code=400, detail="Charger is busy")
    bal = await get_balance(user["user_id"])
    if bal < MIN_START_BALANCE:
        raise HTTPException(status_code=400, detail=f"Minimum wallet balance of ₹{MIN_START_BALANCE:.0f} required")
    existing = await db.sessions.find_one({"user_id": user["user_id"], "status": "active"}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="You already have an active session")
    session = {
        "session_id": nid("sess"), "charger_id": c["charger_id"], "charger_name": c["name"],
        "user_id": user["user_id"], "owner_id": c["owner_id"], "status": "active",
        "price_per_kwh": c["price_per_kwh"], "start_time": iso(), "end_time": None,
        "energy_kwh": 0, "cost": 0,
    }
    await db.sessions.insert_one(dict(session))
    await db.chargers.update_one({"charger_id": c["charger_id"]}, {"$set": {"status": "Charging"}})
    await notify(user["user_id"], "charging_started", f"Charging started at {c['name']}.")
    session.pop("_id", None)
    return session


@api_router.get("/sessions/{session_id}/live")
async def session_live(session_id: str, user=Depends(get_current_user)):
    s = await db.sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not s or s["user_id"] != user["user_id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    c = await db.chargers.find_one({"charger_id": s["charger_id"]}, {"_id": 0})
    bal = await get_balance(user["user_id"])
    live = compute_live(s, c, max_cost=bal)
    return {**s, "live": live}


@api_router.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str, user=Depends(get_current_user)):
    require_demo_finance()
    s = await db.sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not s or s["user_id"] != user["user_id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    if s["status"] != "active":
        raise HTTPException(status_code=400, detail="Session already stopped")
    c = await db.chargers.find_one({"charger_id": s["charger_id"]}, {"_id": 0})
    bal = await get_balance(user["user_id"])
    end = iso()
    s["end_time"] = end
    live = compute_live(s, c, max_cost=bal)  # cost is capped to wallet balance
    energy, cost = live["energy_kwh"], live["cost"]
    await add_wallet_txn(user["user_id"], "charge", -cost, f"Charging at {c['name']} — {energy} kWh")
    owner_amt = round(cost * OWNER_SHARE, 2)
    company_amt = round(cost * COMPANY_SHARE, 2)
    await add_owner_earning(c["owner_id"], owner_amt, f"Session {session_id[:10]} — {energy} kWh")
    await db.sessions.update_one({"session_id": session_id}, {"$set": {
        "status": "completed", "end_time": end, "energy_kwh": energy, "cost": cost,
        "owner_amount": owner_amt, "company_amount": company_amt,
    }})
    await db.chargers.update_one({"charger_id": s["charger_id"]}, {"$set": {"status": "Available", "energy_today": round(c.get("energy_today", 0) + energy, 2)}})
    await notify(user["user_id"], "charging_stopped", f"Charging stopped. {energy} kWh · ₹{cost:.0f} charged.")
    new_bal = await get_balance(user["user_id"])
    if new_bal < MIN_START_BALANCE:
        await notify(user["user_id"], "wallet_low", f"Low wallet balance: ₹{new_bal:.0f}. Please top up.")
    return {"ok": True, "energy_kwh": energy, "cost": cost, "owner_amount": owner_amt, "company_amount": company_amt, "balance": new_bal}


@api_router.get("/sessions")
async def my_sessions(user=Depends(get_current_user)):
    return await db.sessions.find({"user_id": user["user_id"]}, {"_id": 0}).sort("start_time", -1).to_list(200)


# ---------------- Notifications ----------------
@api_router.get("/notifications")
async def notifications(user=Depends(get_current_user)):
    return await db.notifications.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)


@api_router.post("/notifications/read")
async def read_notifications(user=Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["user_id"]}, {"$set": {"read": True}})
    return {"ok": True}


# ---------------- Owner ----------------
async def owner_earnings_window(owner_id, since):
    total = 0.0
    async for s in db.sessions.find({"owner_id": owner_id, "status": "completed"}, {"_id": 0, "start_time": 1, "owner_amount": 1, "energy_kwh": 1}):
        if parse_dt(s["start_time"]) >= since:
            total += s.get("owner_amount", 0)
    return round(total, 2)


@api_router.get("/owner/summary")
async def owner_summary(user=Depends(require("owner", "admin"))):
    oid = user["user_id"]
    today = now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
    month = now_utc().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    sessions = await db.sessions.find({"owner_id": oid, "status": "completed"}, {"_id": 0}).to_list(1000)
    units = round(sum(s.get("energy_kwh", 0) for s in sessions), 2)
    chargers = await db.chargers.find({"owner_id": oid}, {"_id": 0}).to_list(500)
    return {
        "wallet": (await db.owner_wallets.find_one({"user_id": oid}, {"_id": 0}) or {}).get("balance", 0.0),
        "today_earnings": await owner_earnings_window(oid, today),
        "month_earnings": await owner_earnings_window(oid, month),
        "units_sold": units,
        "total_sessions": len(sessions),
        "chargers_total": len(chargers),
        "chargers_online": sum(1 for c in chargers if c.get("online", True) and c["status"] != "Offline"),
    }


@api_router.get("/owner/chargers")
async def owner_chargers(user=Depends(require("owner", "admin"))):
    chargers = await db.chargers.find({"owner_id": user["user_id"]}, {"_id": 0}).sort("charger_id", 1).to_list(500)
    return [telemetry(c) for c in chargers]


@api_router.get("/owner/transactions")
async def owner_txns(user=Depends(require("owner", "admin"))):
    return await db.owner_transactions.find({"owner_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api_router.post("/owner/withdraw")
async def owner_withdraw(body: WithdrawBody, user=Depends(require("owner", "admin"))):
    require_demo_finance()
    bal = (await db.owner_wallets.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}).get("balance", 0.0)
    if body.amount <= 0 or body.amount > bal:
        raise HTTPException(status_code=400, detail="Invalid withdrawal amount")
    wd = {"id": nid("wd"), "owner_id": user["user_id"], "owner_name": user["name"],
          "amount": round(body.amount, 2), "status": "requested", "created_at": iso()}
    await db.withdrawals.insert_one(dict(wd))
    await add_owner_earning(user["user_id"], -body.amount, "Withdrawal request")
    wd.pop("_id", None)
    return {"ok": True, "withdrawal": wd}


@api_router.get("/owner/withdrawals")
async def owner_withdrawals(user=Depends(require("owner", "admin"))):
    return await db.withdrawals.find({"owner_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


# ---------------- Telemetry (charger monitoring) ----------------
def telemetry(c):
    charging = c["status"] == "Charging"
    power = c["max_power_kw"] if charging else 0
    online = c.get("online", True) and c["status"] != "Offline"
    return {
        "charger_id": c["charger_id"], "name": c["name"], "status": c["status"],
        "owner_id": c["owner_id"], "price_per_kwh": c["price_per_kwh"], "connector": c["connector"],
        "max_power_kw": c["max_power_kw"], "location": c.get("location", ""), "online": online,
        "voltage": 230 + random.randint(-4, 4) if online else 0,
        "current": round((power * 1000) / 230, 1) if charging else 0,
        "power_kw": power,
        "energy_today": round(c.get("energy_today", 0), 2),
        "temperature": random.randint(28, 42) if online else 0,
        "signal": random.randint(3, 5) if online else 0,
        "firmware": c.get("firmware", "v1.6.3"),
        "last_heartbeat": iso() if online else c.get("last_heartbeat", iso()),
        "lat": c.get("lat"), "lng": c.get("lng"),
    }


# ---------------- Admin ----------------
@api_router.get("/admin/summary")
async def admin_summary(user=Depends(require("admin"))):
    chargers = await db.chargers.find({}, {"_id": 0}).to_list(1000)
    sessions = await db.sessions.find({"status": "completed"}, {"_id": 0}).to_list(5000)
    revenue = round(sum(s.get("cost", 0) for s in sessions), 2)
    commission = round(sum(s.get("company_amount", 0) for s in sessions), 2)
    units = round(sum(s.get("energy_kwh", 0) for s in sessions), 2)
    return {
        "total_revenue": revenue, "commission": commission, "owner_payouts": round(revenue - commission, 2),
        "units_sold": units, "total_sessions": len(sessions),
        "chargers_total": len(chargers),
        "online": sum(1 for c in chargers if c.get("online", True) and c["status"] not in ("Offline", "Fault")),
        "offline": sum(1 for c in chargers if not c.get("online", True) or c["status"] == "Offline"),
        "faults": sum(1 for c in chargers if c["status"] == "Fault"),
        "customers": await db.users.count_documents({"role": "customer"}),
        "owners": await db.users.count_documents({"role": "owner"}),
    }


@api_router.get("/admin/chargers")
async def admin_chargers(user=Depends(require("admin"))):
    chargers = await db.chargers.find({}, {"_id": 0}).sort("charger_id", 1).to_list(1000)
    out = []
    for c in chargers:
        t = telemetry(c)
        owner = await db.users.find_one({"user_id": c["owner_id"]}, {"_id": 0, "name": 1})
        t["owner_name"] = owner["name"] if owner else "—"
        out.append(t)
    return out


@api_router.post("/admin/chargers")
async def create_charger(body: ChargerCreate, user=Depends(require("admin"))):
    counter = await db.counters.find_one_and_update(
        {"_id": "charger"}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER)
    cid = f"IND{str(counter['seq']).zfill(6)}"
    c = {"charger_id": cid, "name": body.name, "owner_id": body.owner_id, "connector": body.connector,
         "price_per_kwh": body.price_per_kwh, "max_power_kw": body.max_power_kw, "location": body.location,
         "status": "Available", "online": True, "energy_today": 0, "firmware": "v1.6.3", "last_heartbeat": iso(),
         "lat": round(20 + random.uniform(-6, 8), 4), "lng": round(78 + random.uniform(-8, 8), 4),
         "created_at": iso()}
    await db.chargers.insert_one(dict(c))
    c.pop("_id", None)
    return {"ok": True, "charger": c}


@api_router.post("/admin/chargers/{charger_id}/restart")
async def restart_charger(charger_id: str, user=Depends(require("admin"))):
    c = await db.chargers.find_one({"charger_id": charger_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Charger not found")
    await db.chargers.update_one({"charger_id": charger_id}, {"$set": {"status": "Available", "online": True, "last_heartbeat": iso()}})
    await db.fault_logs.insert_one({"id": nid("flt"), "charger_id": charger_id, "message": "Remote restart issued by admin", "severity": "info", "resolved": True, "created_at": iso()})
    return {"ok": True}


@api_router.post("/admin/chargers/{charger_id}/status")
async def set_charger_status(charger_id: str, body: dict, user=Depends(require("admin"))):
    status = body.get("status")
    if status not in ("Available", "Offline", "Fault"):
        raise HTTPException(status_code=400, detail="Invalid status")
    online = status not in ("Offline",)
    await db.chargers.update_one({"charger_id": charger_id}, {"$set": {"status": status, "online": online}})
    if status == "Fault":
        await db.fault_logs.insert_one({"id": nid("flt"), "charger_id": charger_id, "message": "Fault flagged by admin", "severity": "critical", "resolved": False, "created_at": iso()})
    return {"ok": True}


@api_router.get("/admin/owners")
async def admin_owners(user=Depends(require("admin"))):
    owners = await db.users.find({"role": "owner"}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for o in owners:
        o["wallet"] = (await db.owner_wallets.find_one({"user_id": o["user_id"]}, {"_id": 0}) or {}).get("balance", 0.0)
        o["chargers"] = await db.chargers.count_documents({"owner_id": o["user_id"]})
    return owners


@api_router.post("/admin/owners")
async def create_owner(body: OwnerCreate, user=Depends(require("admin"))):
    body.phone = normalize_phone(body.phone)
    if await db.users.find_one({"phone": body.phone}):
        raise HTTPException(status_code=400, detail="Phone already registered")
    o = {"user_id": nid("user"), "phone": body.phone, "name": body.name, "role": "owner", "email": "", "created_at": iso()}
    await db.users.insert_one(dict(o))
    await db.owner_wallets.update_one({"user_id": o["user_id"]}, {"$setOnInsert": {"balance": 0.0}}, upsert=True)
    o.pop("_id", None)
    return {"ok": True, "owner": o}


@api_router.get("/admin/users")
async def admin_users(user=Depends(require("admin"))):
    users = await db.users.find({"role": "customer"}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for u in users:
        u["wallet"] = await get_balance(u["user_id"])
    return users


@api_router.post("/admin/wallet/adjust")
async def admin_wallet_adjust(body: WalletAdjust, user=Depends(require("admin"))):
    require_demo_finance()
    bal = await add_wallet_txn(body.user_id, "adjustment", body.amount, body.note)
    await notify(body.user_id, "payment_successful", f"Wallet adjusted by ₹{body.amount:.0f}. {body.note}")
    return {"ok": True, "balance": bal}


@api_router.get("/admin/faults")
async def admin_faults(user=Depends(require("admin"))):
    return await db.fault_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(300)


@api_router.get("/admin/withdrawals")
async def admin_withdrawals(user=Depends(require("admin"))):
    return await db.withdrawals.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api_router.patch("/admin/withdrawals/{wid}")
async def update_withdrawal(wid: str, body: dict, user=Depends(require("admin"))):
    require_demo_finance()
    status = body.get("status")
    if status not in ("verified", "completed", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid status")
    wd = await db.withdrawals.find_one({"id": wid}, {"_id": 0})
    if not wd:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    await db.withdrawals.update_one({"id": wid}, {"$set": {"status": status}})
    if status == "rejected":
        await add_owner_earning(wd["owner_id"], wd["amount"], "Withdrawal rejected — refunded")
    return {"ok": True}


@api_router.get("/admin/sessions")
async def admin_sessions(user=Depends(require("admin"))):
    return await db.sessions.find({}, {"_id": 0}).sort("start_time", -1).to_list(500)


# ==================== EV Charger Repair Service (Phase 1) ====================
REPAIR_STATUSES = [
    "REQUESTED", "AWAITING_SHIPMENT", "IN_TRANSIT_TO_VOLTX", "RECEIVED_AT_VOLTX",
    "DIAGNOSING", "ESTIMATE_SENT", "CUSTOMER_APPROVED", "CUSTOMER_DECLINED",
    "REPAIRING", "REPAIR_COMPLETED", "PAYMENT_PENDING", "READY_TO_SHIP",
    "SHIPPED_TO_CUSTOMER", "DELIVERED", "COMPLETED", "CANCELLED", "NOT_REPAIRABLE",
]

REPAIR_TRANSITIONS = {
    "REQUESTED": ["AWAITING_SHIPMENT", "CANCELLED"],
    "AWAITING_SHIPMENT": ["IN_TRANSIT_TO_VOLTX", "CANCELLED"],
    "IN_TRANSIT_TO_VOLTX": ["RECEIVED_AT_VOLTX", "CANCELLED"],
    "RECEIVED_AT_VOLTX": ["DIAGNOSING", "CANCELLED"],
    "DIAGNOSING": ["ESTIMATE_SENT", "NOT_REPAIRABLE", "CANCELLED"],
    "ESTIMATE_SENT": ["CUSTOMER_APPROVED", "CUSTOMER_DECLINED", "CANCELLED"],
    "CUSTOMER_APPROVED": ["REPAIRING", "CANCELLED"],
    "CUSTOMER_DECLINED": ["READY_TO_SHIP", "CANCELLED"],
    "NOT_REPAIRABLE": ["READY_TO_SHIP", "CANCELLED"],
    "REPAIRING": ["REPAIR_COMPLETED", "CANCELLED"],
    "REPAIR_COMPLETED": ["PAYMENT_PENDING", "CANCELLED"],
    "PAYMENT_PENDING": ["READY_TO_SHIP", "CANCELLED"],
    "READY_TO_SHIP": ["SHIPPED_TO_CUSTOMER", "CANCELLED"],
    "SHIPPED_TO_CUSTOMER": ["DELIVERED"],
    "DELIVERED": ["COMPLETED"],
    "COMPLETED": [],
    "CANCELLED": [],
}
# Statuses a normal customer/owner may set themselves (others are Voltx/admin-only)
CUSTOMER_SETTABLE = {"AWAITING_SHIPMENT", "IN_TRANSIT_TO_VOLTX", "CUSTOMER_APPROVED", "CUSTOMER_DECLINED", "CANCELLED"}
CHARGER_TYPES = {"AC", "DC", "PORTABLE", "OTHER"}
INTERNAL_DIAGNOSIS_FIELDS = ("technician_notes", "internal_notes", "parts_required")


class ChargerInfo(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    charger_type: Optional[str] = None
    power_rating: Optional[str] = None


class RepairCreate(BaseModel):
    idempotency_key: Optional[str] = Field(None, min_length=1, max_length=128)
    customer_type: Literal["RETAIL", "STATION_OWNER"] = "RETAIL"
    charger_id: Optional[str] = None
    charger_info: Optional[ChargerInfo] = None
    problem_description: str = Field(..., min_length=3)
    reported_category: Optional[str] = None
    photos: Optional[List[str]] = None
    whatsapp_opt_in: StrictBool = False


class RepairStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


class DiagnosisUpdate(BaseModel):
    diagnosis: Optional[str] = None
    identified_fault: Optional[str] = None
    repairability: Optional[str] = None  # REPAIRABLE / NOT_REPAIRABLE / UNKNOWN
    parts_required: Optional[List[str]] = None
    technician_notes: Optional[str] = None
    internal_notes: Optional[str] = None


class EstimatePart(BaseModel):
    _exact_price = field_validator("price", mode="before")(exact_money_input)
    name: str
    qty: int = Field(1, ge=1, le=10000, strict=True)
    price: float = Field(0.0, ge=0, le=99999999.99, allow_inf_nan=False)


class EstimateUpdate(BaseModel):
    _exact_amounts = field_validator(*MONEY_FIELDS, mode="before")(exact_money_input)
    parts: Optional[List[EstimatePart]] = None
    labor: Optional[float] = Field(None, ge=0, le=99999999.99, allow_inf_nan=False)
    diagnostic_fee: Optional[float] = Field(None, ge=0, le=99999999.99, allow_inf_nan=False)
    incoming_logistics_cost: Optional[float] = Field(None, ge=0, le=99999999.99, allow_inf_nan=False)
    return_shipping_cost: Optional[float] = Field(None, ge=0, le=99999999.99, allow_inf_nan=False)
    other_charges: Optional[float] = Field(None, ge=0, le=99999999.99, allow_inf_nan=False)
    tax: Optional[float] = Field(None, ge=0, le=99999999.99, allow_inf_nan=False)
    notes: Optional[str] = None


class PaymentVerification(BaseModel):
    _exact_balance = field_validator("amount_due", mode="before")(exact_money_input)
    idempotency_key: Optional[str] = Field(None, min_length=1, max_length=128)
    amount_due: float = Field(..., ge=0, le=99999999.99, allow_inf_nan=False)
    reference: str = Field(..., min_length=3, max_length=120)


class ShipmentUpdate(BaseModel):
    leg: Literal["incoming", "return"]
    courier: Optional[str] = None
    tracking_number: Optional[str] = None
    shipped_date: Optional[str] = None
    received_date: Optional[str] = None
    delivered_date: Optional[str] = None
    notes: Optional[str] = None


async def next_repair_number():
    c = await db.counters.find_one_and_update(
        {"_id": "repair"}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER)
    return f"REP-{10000 + c['seq']}"  # first request -> REP-10001


async def owner_charger_ids(uid):
    return [c["charger_id"] async for c in db.chargers.find({"owner_id": uid}, {"_id": 0, "charger_id": 1})]


async def can_access_repair(user, r):
    if user.get("role") not in ("customer", "owner", "admin") or not text_fact(user.get("user_id")):
        return False
    if user["role"] == "admin":
        return True
    if not text_fact(r.get("user_id")):
        return False
    if r["user_id"] == user["user_id"]:
        return True
    if user["role"] == "owner" and text_fact(r.get("charger_id")):
        return bool(await db.chargers.find_one({"charger_id": r["charger_id"], "owner_id": user["user_id"]}))
    return False


def require_repair_actor(user, repair):
    if user.get("role") == "admin":
        return
    if user.get("role") not in ("customer", "owner") or not text_fact(user.get("user_id")) or user["user_id"] != repair.get("user_id"):
        raise HTTPException(403, "Only the repair submitter or administrator may change this repair")


def repair_guard(r):
    # Legacy repairs without a revision match null; every relevant writer increments it.
    return {"id": r["id"], "status": r["status"], "revision": r.get("revision")}


def sanitize_repair(r, user):
    r = dict(r)
    r.pop("_id", None)
    r.pop("whatsapp_outbox", None)
    r.pop("whatsapp_consent", None)
    r.pop("revision", None)
    r.pop("creation_key", None)
    r.pop("creation_fingerprint", None)
    r.pop("payment_records", None)
    r.pop("payment_events", None)
    r.pop("payment_evidence", None)
    r.pop("payment_receipt", None)
    if r.get("payment_summary"):
        r["payment_summary"] = {k: v for k, v in r["payment_summary"].items()
                                if k in ("amount_due", "currency", "verified_at")}
    if r.get("return_shipment"):
        r["return_shipment"] = {k: v for k, v in r["return_shipment"].items()
                                if k not in ("confirmed_at", "confirmed_by")}
    if user["role"] != "admin" and r.get("diagnosis"):
        r["diagnosis"] = {k: v for k, v in r["diagnosis"].items() if k not in INTERNAL_DIAGNOSIS_FIELDS}
    if user["role"] != "admin":
        for field in ("incoming_shipment", "return_shipment", "estimate"):
            if r.get(field):
                r[field] = {k: v for k, v in r[field].items() if k != "notes"}
        r["status_history"] = [{k: v for k, v in entry.items() if k not in ("note", "by")} for entry in r.get("status_history", [])]
        if user.get("user_id") != r.get("user_id"):
            # Charger owners can track equipment, not another customer's personal details.
            r = {k: v for k, v in r.items() if k in ("id", "repair_request_number", "charger_id", "status", "created_at", "updated_at")}
    return r


@api_router.post("/repairs")
async def create_repair(body: RepairCreate, user=Depends(get_current_user)):
    if user.get("role") not in ("customer", "owner", "admin") or not text_fact(user.get("user_id")):
        raise HTTPException(403, "Unsupported repair actor")
    payload = body.model_dump(exclude={"idempotency_key"})
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    creation_key = None
    if body.idempotency_key is not None:
        if not text_fact(body.idempotency_key, 128):
            raise HTTPException(400, "Invalid idempotency key")
        creation_key = hashlib.sha256(json.dumps([user["user_id"], body.idempotency_key]).encode()).hexdigest()
        existing = await db.repair_requests.find_one({"creation_key": creation_key})
        if existing:
            if existing["creation_fingerprint"] != fingerprint:
                raise HTTPException(409, "Idempotency key reused with different repair details")
            return sanitize_repair(existing, user)
    charger_id = None
    info = body.charger_info.model_dump() if body.charger_info else {}
    if body.charger_id:
        c = await db.chargers.find_one({"charger_id": body.charger_id}, {"_id": 0})
        if not c:
            raise HTTPException(status_code=404, detail="Charger not found")
        charger_id = c["charger_id"]  # retain relationship, do NOT duplicate the charger
        info.setdefault("brand", c.get("name"))
        info.setdefault("model", c.get("name"))
        info.setdefault("power_rating", f"{c.get('max_power_kw')} kW")
    else:
        if not info.get("brand"):
            raise HTTPException(status_code=400, detail="Charger brand is required for an unregistered charger")
    if info.get("charger_type") and info["charger_type"] not in CHARGER_TYPES:
        raise HTTPException(status_code=400, detail=f"charger_type must be one of {sorted(CHARGER_TYPES)}")
    now = iso()
    consent = consent_record(body.whatsapp_opt_in, user, now)
    event_id = nid("evt")
    r = {
        "id": nid("rep"), "repair_request_number": await next_repair_number(), "user_id": user["user_id"],
        "customer_type": body.customer_type, "charger_id": charger_id, "charger_info": info,
        "problem_description": body.problem_description, "reported_category": body.reported_category,
        "photos": body.photos or [], "status": "REQUESTED", "revision": 0,
        "status_history": [{"event_id": event_id, "status": "REQUESTED", "by": user["user_id"], "at": now, "note": None}],
        "diagnosis": None, "estimate": None, "incoming_shipment": None, "return_shipment": None,
        "created_at": now, "updated_at": now,
    }
    r["whatsapp_consent"] = consent
    event = event_for(r, "REQUESTED", event_id, WhatsAppSettings.from_env(), customer=user)
    r["whatsapp_outbox"] = [event] if event else []
    if creation_key:
        r.update(creation_key=creation_key, creation_fingerprint=fingerprint)
    try:
        await db.repair_requests.insert_one(dict(r))
    except DuplicateKeyError:
        existing = await db.repair_requests.find_one({"creation_key": creation_key}) if creation_key else None
        if not existing or existing.get("creation_fingerprint") != fingerprint:
            raise HTTPException(409, "Conflicting repair submission") from None
        return sanitize_repair(existing, user)
    return sanitize_repair(r, user)


@api_router.get("/repairs")
async def list_repairs(scope: str = "mine", user=Depends(get_current_user), response: Response = None,
                       limit: int = Query(100, ge=1, le=100), cursor: Optional[str] = Query(None, max_length=512)):
    if scope not in ("mine", "all"):
        raise HTTPException(400, "Unsupported repair scope")
    if user.get("role") not in ("customer", "owner", "admin") or not text_fact(user.get("user_id")):
        raise HTTPException(403, "Unsupported repair actor")
    if scope == "all" and user["role"] != "admin":
        raise HTTPException(403, "Only administrators may list all repairs")
    if user["role"] == "admin" and scope == "all":
        q = {}
    elif user["role"] == "owner":
        cids = await owner_charger_ids(user["user_id"])
        q = {"$or": [{"user_id": user["user_id"]}, {"charger_id": {"$in": cids}, "user_id": {"$type": "string", "$ne": ""}}]}
    else:
        q = {"user_id": user["user_id"]}
    if cursor:
        try:
            at, rid = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
            if not text_fact(at, 64) or not text_fact(rid, 128):
                raise ValueError()
        except (ValueError, TypeError, UnicodeError):
            raise HTTPException(400, "Invalid repair cursor") from None
        q = {"$and": [q, {"$or": [{"created_at": {"$lt": at}}, {"created_at": at, "id": {"$lt": rid}}]}]}
    projection = {key: 0 for key in ("_id", "photos", "whatsapp_outbox", "whatsapp_consent", "payment_records", "payment_events", "payment_evidence", "payment_receipt", "creation_key", "creation_fingerprint")}
    docs = await db.repair_requests.find(q, projection).sort([("created_at", -1), ("id", -1)]).to_list(limit + 1)
    if len(docs) > limit and response is not None:
        last = docs[limit - 1]
        response.headers["X-Next-Cursor"] = base64.urlsafe_b64encode(json.dumps([last["created_at"], last["id"]]).encode()).decode()
    return [sanitize_repair(d, user) for d in docs[:limit]]


@api_router.get("/repairs/{rid}")
async def get_repair(rid: str, user=Depends(get_current_user)):
    r = await db.repair_requests.find_one({"id": rid}, {"_id": 0})
    if not r:
        raise HTTPException(status_code=404, detail="Repair request not found")
    if not await can_access_repair(user, r):
        raise HTTPException(status_code=403, detail="Not authorized for this repair request")
    return sanitize_repair(r, user)


@api_router.patch("/repairs/{rid}/status")
async def update_repair_status(rid: str, body: RepairStatusUpdate, user=Depends(get_current_user)):
    r = await db.repair_requests.find_one({"id": rid}, {"_id": 0})
    if not r:
        raise HTTPException(status_code=404, detail="Repair request not found")
    require_repair_actor(user, r)
    if not await can_access_repair(user, r):
        raise HTTPException(status_code=403, detail="Not authorized for this repair request")
    target = body.status
    if target not in REPAIR_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if target not in REPAIR_TRANSITIONS.get(r["status"], []):
        raise HTTPException(status_code=400, detail=f"Cannot transition from {r['status']} to {target}")
    if user["role"] != "admin" and target not in CUSTOMER_SETTABLE:
        raise HTTPException(status_code=403, detail="This status change is restricted to the RushX repair team")
    if target in ("CUSTOMER_APPROVED", "CUSTOMER_DECLINED") and not r.get("estimate"):
        raise HTTPException(status_code=400, detail="No estimate available to approve or decline")
    if target == "CANCELLED" and r.get("payment_receipt"):
        raise HTTPException(409, "A verified payment requires a reviewed refund or cancellation workflow")
    validate_transition_facts(r, target)
    now = iso()
    upd = {"status": target, "updated_at": now}
    if target == "ESTIMATE_SENT" and r.get("estimate"):
        upd["estimate.status"] = "SENT"
        upd["estimate.published_at"] = now
    if target == "CUSTOMER_APPROVED":
        upd["estimate.status"] = "APPROVED"
        upd["estimate.approved_at"] = now
    if target == "CUSTOMER_DECLINED":
        upd["estimate.status"] = "DECLINED"
        upd["estimate.declined_at"] = now
    event_id = nid("evt")
    pushes = {"status_history": {"event_id": event_id, "status": target, "by": user["user_id"], "at": now, "note": body.note}}
    settings = WhatsAppSettings.from_env()
    customer = None
    if settings.enabled and r.get("whatsapp_consent", {}).get("opted_in"):
        customer = await db.users.find_one({"user_id": r["user_id"]}, {"name": 1})
    event = event_for(r, target, event_id, settings, customer=customer)
    if event:
        pushes["whatsapp_outbox"] = event
    result = await db.repair_requests.update_one(repair_guard(r), {
        "$set": upd, "$push": pushes, "$inc": {"revision": 1},
    })
    if not result.modified_count:
        raise HTTPException(status_code=409, detail="Repair status changed; refresh and try again")
    r = await db.repair_requests.find_one({"id": rid}, {"_id": 0})
    return sanitize_repair(r, user)


@api_router.patch("/repairs/{rid}/diagnosis")
async def update_repair_diagnosis(rid: str, body: DiagnosisUpdate, user=Depends(require("admin"))):
    r = await db.repair_requests.find_one({"id": rid}, {"_id": 0})
    if not r:
        raise HTTPException(status_code=404, detail="Repair request not found")
    if r["status"] not in ("REQUESTED", "AWAITING_SHIPMENT", "IN_TRANSIT_TO_VOLTX", "RECEIVED_AT_VOLTX", "DIAGNOSING"):
        raise HTTPException(409, "Diagnosis is locked after inspection")
    d = r.get("diagnosis") or {}
    d.update(body.model_dump(exclude_none=True))
    d["diagnosed_at"] = iso()
    result = await db.repair_requests.update_one(repair_guard(r), {"$set": {"diagnosis": d, "updated_at": iso()}, "$inc": {"revision": 1}})
    if not result.modified_count:
        raise HTTPException(409, "Repair changed; refresh and try again")
    return {"ok": True, "diagnosis": d}


@api_router.patch("/repairs/{rid}/estimate")
async def update_repair_estimate(rid: str, body: EstimateUpdate, user=Depends(require("admin"))):
    r = await db.repair_requests.find_one({"id": rid}, {"_id": 0})
    if not r:
        raise HTTPException(status_code=404, detail="Repair request not found")
    if r["status"] not in ("REQUESTED", "AWAITING_SHIPMENT", "IN_TRANSIT_TO_VOLTX", "RECEIVED_AT_VOLTX", "DIAGNOSING"):
        raise HTTPException(409, "Estimate drafting is closed for this repair")
    if (r.get("estimate") or {}).get("status", "DRAFT") != "DRAFT":
        raise HTTPException(409, "Published estimates are immutable; contact support for a revised quote")
    e = r.get("estimate") or {"status": "DRAFT", "created_at": iso(), "approved_at": None, "declined_at": None}
    data = body.model_dump(exclude_none=True)
    if "parts" in data:
        e["parts"] = data.pop("parts")
    e.update(data)
    total = calculated_estimate(e)
    e["subtotal"] = float(total - money(e.get("tax", 0)))
    e["total"] = float(total)
    e["currency"] = "INR"
    e["total_minor"] = int(total * 100)
    e["amounts_minor"] = {key: int(money(e.get(key, 0)) * 100) for key in MONEY_FIELDS}
    for part in e.get("parts", []):
        part["price_minor"] = int(money(part.get("price", 0)) * 100)
    e["updated_at"] = iso()
    result = await db.repair_requests.update_one(repair_guard(r), {
        "$set": {"estimate": e, "updated_at": iso()}, "$inc": {"revision": 1}})
    if not result.modified_count:
        raise HTTPException(409, "Repair changed; refresh and try again")
    return {"ok": True, "estimate": e}


@api_router.patch("/repairs/{rid}/shipment")
async def update_repair_shipment(rid: str, body: ShipmentUpdate, user=Depends(get_current_user)):
    r = await db.repair_requests.find_one({"id": rid}, {"_id": 0})
    if not r:
        raise HTTPException(status_code=404, detail="Repair request not found")
    require_repair_actor(user, r)
    if not await can_access_repair(user, r):
        raise HTTPException(status_code=403, detail="Not authorized for this repair request")
    if body.leg == "return" and user["role"] != "admin":
        raise HTTPException(403, "Return shipment details must be confirmed by the RushX repair team")
    if body.leg == "incoming" and user["role"] != "admin":
        if r["status"] not in ("REQUESTED", "AWAITING_SHIPMENT", "IN_TRANSIT_TO_VOLTX"):
            raise HTTPException(409, "Incoming shipment is locked after receipt")
        if body.received_date is not None or body.delivered_date is not None:
            raise HTTPException(403, "Only staff may confirm incoming receipt")
    if r["status"] in ("CANCELLED", "COMPLETED"):
        raise HTTPException(409, "Closed repair shipment is locked")
    key = "incoming_shipment" if body.leg == "incoming" else "return_shipment"
    s = r.get(key) or {}
    if body.leg == "return" and r["status"] in ("SHIPPED_TO_CUSTOMER", "DELIVERED", "COMPLETED"):
        if any(getattr(body, k) is not None and getattr(body, k) != s.get(k) for k in ("courier", "tracking_number")):
            raise HTTPException(409, "Dispatched courier and tracking details are immutable; contact support")
    s.update({k: v for k, v in body.model_dump(exclude_none=True).items() if k != "leg"})
    if body.leg == "return":
        if text_fact(s.get("courier"), 128) and text_fact(s.get("tracking_number"), 128):
            s.update(confirmed_at=iso(), confirmed_by=user["user_id"])
        else:
            s.pop("confirmed_at", None)
            s.pop("confirmed_by", None)
    result = await db.repair_requests.update_one(repair_guard(r), {
        "$set": {key: s, "updated_at": iso()}, "$inc": {"revision": 1}})
    if not result.modified_count:
        raise HTTPException(409, "Repair changed; refresh and try again")
    r = await db.repair_requests.find_one({"id": rid}, {"_id": 0})
    return sanitize_repair(r, user)


def payment_service():
    settings = WhatsAppSettings.from_env()
    return PaymentService(MongoPaymentRepository(db.repair_requests, db.payment_references),
                          ManualPaymentProcessor(),
                          lambda repair, event, customer: payment_received_notification(
                              repair, event, settings, customer))


class PaymentEvidence(BaseModel):
    reference: str = Field(..., min_length=3, max_length=120)


class PaymentReceiptVerification(BaseModel):
    amount: Decimal = Field(..., gt=0, le=Decimal("99999999.99"), max_digits=10, decimal_places=2, allow_inf_nan=False)
    method: Literal["upi", "bank_transfer", "cash"]
    reference: Optional[str] = Field(None, max_length=120)
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    funds_received: StrictBool

    @field_validator("amount", mode="before")
    @classmethod
    def amount_is_numeric(cls, value):
        if isinstance(value, bool):
            raise ValueError("Amount must be numeric")
        return value


@api_router.get("/repairs/{rid}/payment")
async def get_repair_payment(rid: str, user=Depends(get_current_user)):
    if user.get("role") not in ("customer", "owner", "admin") or not text_fact(user.get("user_id")):
        raise HTTPException(403, "Unsupported payment actor")
    repair = await db.repair_requests.find_one({"id": rid})
    if not repair:
        raise HTTPException(404, "Repair request not found")
    if user["role"] != "admin" and repair["user_id"] != user["user_id"]:
        raise HTTPException(403, "Not authorized for this payment")
    summary = repair.get("payment_summary") or {}
    receipt = repair.get("payment_receipt") or {}
    result = {"state": summary.get("state", "PENDING" if summary else "UNVERIFIED"),
              "amount_due": summary.get("amount_due"), "currency": "INR",
              "receipt": {k: receipt[k] for k in ("id", "verified_amount", "safe_reference", "verified_at", "method") if k in receipt},
              **public_payment_instructions()}
    if user["role"] == "admin":
        result["evidence"] = repair.get("payment_evidence", [])
        result["audit"] = repair.get("payment_records", [])
        result["verified_receipt"] = receipt
    return result


@api_router.post("/repairs/{rid}/payment/reference")
async def submit_payment_reference(rid: str, body: PaymentEvidence, user=Depends(get_current_user)):
    if user.get("role") not in ("customer", "owner", "admin") or not text_fact(user.get("user_id")):
        raise HTTPException(403, "Unsupported payment actor")
    return await payment_service().submit_reference(rid, body.reference, user["user_id"])


@api_router.post("/repairs/{rid}/payment/verify")
async def receive_repair_payment(rid: str, body: PaymentReceiptVerification, user=Depends(require("admin"))):
    repair = await db.repair_requests.find_one({"id": rid})
    customer = await db.users.find_one({"user_id": repair["user_id"]}, {"name": 1}) if repair else None
    return await payment_service().receive(rid, body.amount, body.method, body.reference,
                                          user["user_id"], body.idempotency_key,
                                          body.funds_received, customer)


@api_router.patch("/repairs/{rid}/payment")
async def verify_repair_payment(rid: str, body: PaymentVerification, user=Depends(require("admin"))):
    return await payment_service().verify_balance(
        rid, body.amount_due, body.reference, user["user_id"], body.idempotency_key)


@api_router.delete("/repairs/{rid}/whatsapp-consent")
async def withdraw_whatsapp_consent(rid: str, user=Depends(get_current_user)):
    r = await db.repair_requests.find_one({"id": rid}, {"_id": 0})
    if not r:
        raise HTTPException(404, "Repair request not found")
    require_repair_actor(user, r)
    if user["role"] != "admin" and user["user_id"] != r["user_id"]:
        raise HTTPException(403, "Only the customer or support can withdraw consent")
    if not r.get("whatsapp_consent", {}).get("opted_in"):
        return {"ok": True}
    result = await db.repair_requests.update_one(repair_guard(r), {"$set": {
        "whatsapp_consent.opted_in": False, "whatsapp_consent.withdrawn_at": iso(),
        "updated_at": iso()}, "$inc": {"revision": 1}})
    if not result.modified_count:
        raise HTTPException(409, "Repair changed; refresh and try again")
    return {"ok": True}


@api_router.get("/admin/whatsapp/metrics")
async def whatsapp_metrics(user=Depends(require("admin"))):
    return await WhatsAppService(db, WhatsAppSettings.from_env()).metrics()


@api_router.post("/admin/whatsapp/jobs/{job_id}/retry")
async def retry_whatsapp_job(job_id: str, user=Depends(require("admin"))):
    await WhatsAppService(db, WhatsAppSettings.from_env()).safe_requeue(job_id)
    return {"ok": True}


# ================== End Repair Service (Phase 1) ==================


@api_router.get("/")
async def root():
    return {"message": "EV Charging Network API"}


@app.exception_handler(RequestValidationError)
async def safe_validation(request: Request, error: RequestValidationError):
    if request.scope["path"].startswith("/api/auth/"):
        return JSONResponse({"detail": "Check the supplied authentication fields."}, status_code=422)
    return await request_validation_exception_handler(request, error)


@app.middleware("http")
async def trusted_origin(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS") and request.scope["path"] != "/api/webhooks/whatsapp":
        if request.headers.get("origin") not in auth_settings.origins:
            return JSONResponse({"detail": "Request origin is not allowed"}, status_code=403)
    response = await call_next(request)
    if request.scope["path"].startswith("/api/auth/"):
        response.headers["Cache-Control"] = "no-store"
    return response


api_router.include_router(webhook_router(lambda: db, lambda: WhatsAppSettings.from_env()))
app.include_router(api_router)
app.add_middleware(
    CORSMiddleware, allow_credentials=True,
    allow_origins=list(auth_settings.origins),
    allow_methods=["*"], allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("uvicorn.access").addFilter(WebhookAccessLogFilter())


@app.on_event("startup")
async def seed():
    await initialize_safety_indexes(db)
    await auth_service.initialize()
    if auth_settings.otp_mode != "demo":
        return
    # Admin
    admin = await db.users.find_one({"phone": "+919000000001"})
    if not admin:
        admin = {"user_id": nid("user"), "phone": "+919000000001", "name": "Network Admin",
                 "role": "admin", "email": ADMIN_EMAIL, "created_at": iso()}
        await db.users.insert_one(dict(admin))
    admin_id = admin["user_id"]
    # Owner
    owner = await db.users.find_one({"phone": "+919000000002"})
    if not owner:
        owner = {"user_id": nid("user"), "phone": "+919000000002", "name": "Ramesh Kumar",
                 "role": "owner", "email": "", "created_at": iso()}
        await db.users.insert_one(dict(owner))
        await db.owner_wallets.update_one({"user_id": owner["user_id"]}, {"$setOnInsert": {"balance": 0.0}}, upsert=True)
    owner_id = owner["user_id"]
    # Customer demo
    cust = await db.users.find_one({"phone": "+919000000003"})
    if not cust:
        cust = {"user_id": nid("user"), "phone": "+919000000003", "name": "Test Customer",
                "role": "customer", "email": "", "created_at": iso()}
        await db.users.insert_one(dict(cust))
        await db.wallets.update_one({"user_id": cust["user_id"]}, {"$setOnInsert": {"balance": 1000.0}}, upsert=True)
    # Chargers
    if await db.chargers.count_documents({}) == 0:
        specs = [
            ("Koregaon Park Station", "Type 2", 15.0, 7.4, "Pune, MH", "Available"),
            ("Cyber Hub Fast Charger", "CCS2", 18.0, 22.0, "Gurugram, HR", "Available"),
            ("MG Road Mall", "Type 2", 16.0, 11.0, "Bengaluru, KA", "Charging"),
            ("Marine Drive Point", "Type 2", 17.0, 7.4, "Mumbai, MH", "Available"),
            ("Sector 62 Depot", "CCS2", 14.0, 22.0, "Noida, UP", "Offline"),
            ("Anna Nagar Hub", "Type 2", 15.5, 11.0, "Chennai, TN", "Fault"),
        ]
        for i, (name, conn, price, power, loc, status) in enumerate(specs, 1):
            await db.chargers.insert_one({
                "charger_id": f"IND{str(i).zfill(6)}", "name": name, "owner_id": owner_id,
                "connector": conn, "price_per_kwh": price, "max_power_kw": power, "location": loc,
                "status": status, "online": status not in ("Offline",),
                "energy_today": round(random.uniform(0, 60), 1), "firmware": "v1.6.3",
                "last_heartbeat": iso(), "created_at": iso(),
            })
        await db.fault_logs.insert_one({"id": nid("flt"), "charger_id": "IND000006", "message": "Over-temperature protection triggered", "severity": "critical", "resolved": False, "created_at": iso()})
    # keep charger id counter in sync with existing chargers
    total_chargers = await db.chargers.count_documents({})
    await db.counters.update_one({"_id": "charger"}, {"$max": {"seq": total_chargers}}, upsert=True)
    coords = {
        "IND000001": (18.5362, 73.8931), "IND000002": (28.4949, 77.0895),
        "IND000003": (12.9756, 77.6068), "IND000004": (18.9430, 72.8238),
        "IND000005": (28.6271, 77.3654), "IND000006": (13.0860, 80.2101),
    }
    for cid, (lat, lng) in coords.items():
        await db.chargers.update_one({"charger_id": cid}, {"$set": {"lat": lat, "lng": lng}})

    # Opt-in local discovery fixtures; never overwrite existing charger state.
    await seed_demo_chargers(db, owner_id)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
