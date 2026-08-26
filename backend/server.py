from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import math
import random
import jwt
from pymongo import ReturnDocument
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALG = "HS256"
DEMO_OTP = "123456"
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
class OTPRequest(BaseModel):
    phone: str


class OTPVerify(BaseModel):
    phone: str
    otp: str
    name: Optional[str] = None


class TopupBody(BaseModel):
    amount: float


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
def make_token(user):
    payload = {"sub": user["user_id"], "role": user["role"], "exp": now_utc() + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(request: Request):
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require(*roles):
    async def dep(user=Depends(get_current_user)):
        if user["role"] not in roles:
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
@api_router.post("/auth/request-otp")
async def request_otp(body: OTPRequest):
    await db.otp_requests.insert_one({"phone": body.phone, "created_at": iso()})
    # DEMO: OTP is fixed and returned in response (no SMS gateway)
    return {"ok": True, "demo_otp": DEMO_OTP, "message": f"OTP sent to {body.phone} (demo code: {DEMO_OTP})"}


@api_router.post("/auth/verify-otp")
async def verify_otp(body: OTPVerify):
    if body.otp != DEMO_OTP:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    user = await db.users.find_one({"phone": body.phone}, {"_id": 0})
    if not user:
        user = {
            "user_id": nid("user"), "phone": body.phone, "name": body.name or "Customer",
            "role": "customer", "email": "", "created_at": iso(),
        }
        await db.users.insert_one(dict(user))
        await db.wallets.update_one({"user_id": user["user_id"]}, {"$setOnInsert": {"balance": 0.0}}, upsert=True)
    token = make_token(user)
    user.pop("_id", None)
    return {"token": token, "user": user}


@api_router.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return user


@api_router.post("/auth/logout")
async def logout():
    return {"ok": True}


# ---------------- Wallet (customer) ----------------
@api_router.get("/wallet")
async def wallet(user=Depends(get_current_user)):
    return {"balance": await get_balance(user["user_id"])}


@api_router.post("/wallet/topup")
async def topup(body: TopupBody, user=Depends(get_current_user)):
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


@api_router.get("/")
async def root():
    return {"message": "EV Charging Network API"}


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware, allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"], allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def seed():
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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
