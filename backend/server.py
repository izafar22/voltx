from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

ADMIN_EMAIL = "crazycoder4192@gmail.com"
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


def now_utc():
    return datetime.now(timezone.utc)


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------- Models ----------------
class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = ""
    role: str = "customer"
    created_at: datetime = Field(default_factory=now_utc)


class LeadCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    company: Optional[str] = ""
    segment: Optional[str] = "Residential"
    product: Optional[str] = ""
    message: str
    source: Optional[str] = "website"


class BookingCreate(BaseModel):
    service_type: str
    date: str
    slot: str
    device: Optional[str] = ""
    description: str


class SubscribeRequest(BaseModel):
    plan_id: str


class QuoteDecision(BaseModel):
    decision: str  # approved / declined


class LeadUpdate(BaseModel):
    status: str


class BookingAssign(BaseModel):
    status: Optional[str] = None
    technician: Optional[str] = None


class QuoteCreate(BaseModel):
    user_id: str
    lead_id: Optional[str] = ""
    title: str
    amount: float
    details: str


# ---------------- Auth helpers ----------------
async def get_current_user(request: Request) -> User:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires_at = session["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now_utc():
        raise HTTPException(status_code=401, detail="Session expired")
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user_doc)


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---------------- Auth routes ----------------
@api_router.post("/auth/session")
async def create_session(request: Request, response: Response):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session id")
    async with httpx.AsyncClient() as hc:
        r = await hc.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": session_id})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session id")
    data = r.json()
    email = data["email"]
    role = "admin" if email == ADMIN_EMAIL else "customer"
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one({"user_id": user_id},
                                  {"$set": {"name": data.get("name"), "picture": data.get("picture"), "role": role}})
    else:
        user_id = new_id("user")
        await db.users.insert_one({
            "user_id": user_id, "email": email, "name": data.get("name", ""),
            "picture": data.get("picture", ""), "role": role, "created_at": now_utc().isoformat(),
        })
    session_token = data["session_token"]
    expires_at = now_utc() + timedelta(days=7)
    await db.user_sessions.update_one(
        {"session_token": session_token},
        {"$set": {"user_id": user_id, "session_token": session_token, "expires_at": expires_at.isoformat(), "created_at": now_utc().isoformat()}},
        upsert=True,
    )
    response.set_cookie(key="session_token", value=session_token, httponly=True, secure=True,
                        samesite="none", path="/", max_age=7 * 24 * 60 * 60)
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return User(**user_doc)


@api_router.get("/auth/me", response_model=User)
async def auth_me(user: User = Depends(get_current_user)):
    return user


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


# ---------------- Public: products & plans ----------------
@api_router.get("/products")
async def get_products():
    return await db.products.find({}, {"_id": 0}).to_list(100)


@api_router.get("/products/{slug}")
async def get_product(slug: str):
    p = await db.products.find_one({"slug": slug}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return p


@api_router.get("/amc-plans")
async def get_amc_plans():
    return await db.amc_plans.find({}, {"_id": 0}).sort("order", 1).to_list(100)


# ---------------- Leads (quote capture) ----------------
@api_router.post("/leads")
async def create_lead(payload: LeadCreate):
    lead = payload.model_dump()
    lead["id"] = new_id("lead")
    lead["status"] = "New"
    lead["created_at"] = now_utc().isoformat()
    await db.leads.insert_one(lead)
    # MOCKED WhatsApp acknowledgment
    await db.messages.insert_one({
        "id": new_id("msg"), "channel": "whatsapp", "to": payload.phone,
        "body": f"Hi {payload.name}, thanks for reaching out to RUSHX! Our team will contact you shortly regarding your {payload.product or 'enquiry'}.",
        "ref": lead["id"], "created_at": now_utc().isoformat(),
    })
    lead.pop("_id", None)
    return {"ok": True, "lead_id": lead["id"], "whatsapp_sent": True}


@api_router.get("/admin/leads")
async def admin_leads(admin: User = Depends(require_admin)):
    return await db.leads.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api_router.patch("/admin/leads/{lead_id}")
async def update_lead(lead_id: str, payload: LeadUpdate, admin: User = Depends(require_admin)):
    await db.leads.update_one({"id": lead_id}, {"$set": {"status": payload.status}})
    return {"ok": True}


# ---------------- Bookings ----------------
@api_router.post("/bookings")
async def create_booking(payload: BookingCreate, user: User = Depends(get_current_user)):
    booking = payload.model_dump()
    booking["id"] = new_id("bk")
    booking["user_id"] = user.user_id
    booking["customer_name"] = user.name
    booking["customer_email"] = user.email
    booking["status"] = "Requested"
    booking["technician"] = ""
    booking["created_at"] = now_utc().isoformat()
    await db.bookings.insert_one(booking)
    await db.messages.insert_one({
        "id": new_id("msg"), "channel": "whatsapp", "to": user.email,
        "body": f"Your RUSHX {payload.service_type} booking for {payload.date} ({payload.slot}) is confirmed. We'll assign a technician soon.",
        "ref": booking["id"], "created_at": now_utc().isoformat(),
    })
    booking.pop("_id", None)
    return {"ok": True, "booking": booking}


@api_router.get("/bookings")
async def my_bookings(user: User = Depends(get_current_user)):
    return await db.bookings.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api_router.get("/admin/bookings")
async def admin_bookings(admin: User = Depends(require_admin)):
    return await db.bookings.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api_router.patch("/admin/bookings/{booking_id}")
async def update_booking(booking_id: str, payload: BookingAssign, admin: User = Depends(require_admin)):
    upd = {k: v for k, v in payload.model_dump().items() if v is not None}
    if upd:
        await db.bookings.update_one({"id": booking_id}, {"$set": upd})
    return {"ok": True}


# ---------------- AMC Subscriptions (Razorpay MOCKED) ----------------
@api_router.post("/subscriptions")
async def subscribe(payload: SubscribeRequest, user: User = Depends(get_current_user)):
    plan = await db.amc_plans.find_one({"id": payload.plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    # MOCKED Razorpay recurring subscription
    await db.subscriptions.update_many({"user_id": user.user_id, "status": "active"}, {"$set": {"status": "cancelled"}})
    sub = {
        "id": new_id("sub"), "user_id": user.user_id, "customer_name": user.name, "customer_email": user.email,
        "plan_id": plan["id"], "plan_name": plan["name"], "amount": plan["price"], "status": "active",
        "razorpay_subscription_id": "MOCK_" + uuid.uuid4().hex[:10],
        "started_at": now_utc().isoformat(),
        "next_billing": (now_utc() + timedelta(days=365)).isoformat(),
    }
    await db.subscriptions.insert_one(sub)
    await db.invoices.insert_one({
        "id": new_id("inv"), "user_id": user.user_id, "customer_email": user.email,
        "subscription_id": sub["id"], "amount": plan["price"], "plan_name": plan["name"],
        "status": "paid", "created_at": now_utc().isoformat(),
    })
    await db.messages.insert_one({
        "id": new_id("msg"), "channel": "whatsapp", "to": user.email,
        "body": f"Welcome to RUSHX {plan['name']} AMC! Your preventive maintenance visits are now active.",
        "ref": sub["id"], "created_at": now_utc().isoformat(),
    })
    sub.pop("_id", None)
    return {"ok": True, "subscription": sub}


@api_router.get("/subscriptions/me")
async def my_subscription(user: User = Depends(get_current_user)):
    sub = await db.subscriptions.find_one({"user_id": user.user_id, "status": "active"}, {"_id": 0})
    return sub or {}


@api_router.post("/subscriptions/cancel")
async def cancel_subscription(user: User = Depends(get_current_user)):
    await db.subscriptions.update_many({"user_id": user.user_id, "status": "active"}, {"$set": {"status": "cancelled"}})
    return {"ok": True}


@api_router.get("/invoices")
async def my_invoices(user: User = Depends(get_current_user)):
    return await db.invoices.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api_router.get("/admin/subscriptions")
async def admin_subscriptions(admin: User = Depends(require_admin)):
    return await db.subscriptions.find({}, {"_id": 0}).sort("started_at", -1).to_list(500)


# ---------------- Quotes ----------------
@api_router.get("/quotes")
async def my_quotes(user: User = Depends(get_current_user)):
    return await db.quotes.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api_router.patch("/quotes/{quote_id}")
async def decide_quote(quote_id: str, payload: QuoteDecision, user: User = Depends(get_current_user)):
    q = await db.quotes.find_one({"id": quote_id, "user_id": user.user_id}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    await db.quotes.update_one({"id": quote_id}, {"$set": {"status": payload.decision}})
    return {"ok": True}


@api_router.post("/admin/quotes")
async def create_quote(payload: QuoteCreate, admin: User = Depends(require_admin)):
    q = payload.model_dump()
    q["id"] = new_id("qt")
    q["status"] = "pending"
    q["created_at"] = now_utc().isoformat()
    await db.quotes.insert_one(q)
    q.pop("_id", None)
    return {"ok": True, "quote": q}


# ---------------- Admin overview ----------------
@api_router.get("/admin/stats")
async def admin_stats(admin: User = Depends(require_admin)):
    return {
        "leads": await db.leads.count_documents({}),
        "new_leads": await db.leads.count_documents({"status": "New"}),
        "customers": await db.users.count_documents({"role": "customer"}),
        "bookings": await db.bookings.count_documents({}),
        "active_subscriptions": await db.subscriptions.count_documents({"status": "active"}),
        "revenue": sum([i["amount"] async for i in db.invoices.find({"status": "paid"}, {"_id": 0, "amount": 1})]),
    }


@api_router.get("/admin/customers")
async def admin_customers(admin: User = Depends(require_admin)):
    return await db.users.find({"role": "customer"}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api_router.get("/admin/messages")
async def admin_messages(admin: User = Depends(require_admin)):
    return await db.messages.find({}, {"_id": 0}).sort("created_at", -1).to_list(300)


@api_router.get("/")
async def root():
    return {"message": "RUSHX API"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ---------------- Seed data ----------------
SEED_PRODUCTS = [
    {"slug": "portable-charger", "name": "RUSHX Portable Charger", "category": "EV Charger", "power": "3.3 kW",
     "tagline": "Charge anywhere, anytime", "price_range": "₹12,000 – ₹18,000",
     "image": "https://images.unsplash.com/photo-1593941707882-a5bba14938c7?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200",
     "description": "A compact, travel-ready AC charger designed for Indian voltage conditions with built-in surge protection.",
     "specs": ["3.3 kW output", "Type 2 / Bharat AC-001 connectors", "IP65 weatherproof", "Overload & surge protection", "6-8 hr full charge"]},
    {"slug": "home-7kw", "name": "RUSHX Home 7.4kW", "category": "EV Charger", "power": "7.4 kW",
     "tagline": "The perfect home wallbox", "price_range": "₹32,000 – ₹45,000",
     "image": "https://images.pexels.com/photos/27355831/pexels-photo-27355831.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
     "description": "Smart wall-mounted charger for homes and apartments with app control and scheduled charging.",
     "specs": ["7.4 kW single phase", "Wi-Fi + app control", "Scheduled charging", "RFID access", "Dynamic load balancing"]},
    {"slug": "commercial-11kw", "name": "RUSHX Commercial 11kW", "category": "EV Charger", "power": "11 kW",
     "tagline": "Reliable workplace charging", "price_range": "₹65,000 – ₹85,000",
     "image": "https://images.unsplash.com/photo-1717386255773-1e3037c81788?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200",
     "description": "Three-phase charger for offices, hotels and dealerships with OCPP-ready architecture.",
     "specs": ["11 kW three phase", "OCPP 1.6 ready", "OLED display", "Multi-user billing", "Weatherproof enclosure"]},
    {"slug": "commercial-22kw", "name": "RUSHX Commercial 22kW", "category": "EV Charger", "power": "22 kW",
     "tagline": "Fast charging for fleets", "price_range": "₹1,10,000 – ₹1,45,000",
     "image": "https://images.unsplash.com/photo-1593941707882-a5bba14938c7?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200",
     "description": "High-power AC charger for commercial fleets and charging station operators.",
     "specs": ["22 kW three phase", "Dual gun option", "Load management", "Remote monitoring", "Robust industrial build"]},
    {"slug": "powerboy-powerwall", "name": "PowerBoy Powerwall (BESS)", "category": "BESS", "power": "5–15 kWh",
     "tagline": "Store energy, cut bills", "price_range": "₹2,50,000+",
     "image": "https://static.prod-images.emergentagent.com/jobs/87d37b59-a517-4add-ac40-bf1c664fa6e7/images/521e35cef9d9fe4ed82d9a2acce22b5cac28397d427c2db5b834f261625dfe0d.jpeg",
     "description": "Modular battery energy storage system for homes and businesses to store solar and grid power.",
     "specs": ["Modular 5–15 kWh", "LFP battery chemistry", "Backup power (UPS mode)", "Solar-ready", "10-year warranty"]},
    {"slug": "hearth-solar-inverter", "name": "Hearth Solar Inverter", "category": "Solar", "power": "3–10 kW",
     "tagline": "Sunshine to savings", "price_range": "₹85,000+",
     "image": "https://images.unsplash.com/photo-1780445392694-c95056ed12e2?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200",
     "description": "Hybrid solar inverter engineered for Indian rooftops with high MPPT efficiency.",
     "specs": ["3–10 kW hybrid", "Dual MPPT", "98% efficiency", "App monitoring", "Grid + battery hybrid"]},
]

SEED_PLANS = [
    {"id": "plan_basic", "name": "Basic", "price": 4999, "order": 1, "period": "year",
     "tagline": "Essential cover for home chargers",
     "features": ["2 preventive visits/year", "Remote diagnostics", "Genuine spare parts (chargeable)", "48-hr response time"]},
    {"id": "plan_standard", "name": "Standard", "price": 9999, "order": 2, "period": "year", "popular": True,
     "tagline": "Best value for businesses",
     "features": ["4 preventive visits/year", "Priority support", "PCB-level repair included", "Free minor spares", "24-hr response time"]},
    {"id": "plan_premium", "name": "Premium", "price": 18999, "order": 3, "period": "year",
     "tagline": "Enterprise-grade peace of mind",
     "features": ["Unlimited visits", "Dedicated account manager", "All spares & PCB repair free", "Same-day response", "Annual health report"]},
]


@app.on_event("startup")
async def seed():
    if await db.products.count_documents({}) == 0:
        await db.products.insert_many([dict(p) for p in SEED_PRODUCTS])
        logger.info("Seeded products")
    else:
        for p in SEED_PRODUCTS:
            await db.products.update_one({"slug": p["slug"]}, {"$set": p}, upsert=True)
    await db.amc_plans.delete_many({})
    await db.amc_plans.insert_many([dict(p) for p in SEED_PLANS])
    # ensure admin user exists
    await db.users.update_one({"email": ADMIN_EMAIL}, {"$setOnInsert": {
        "user_id": new_id("user"), "email": ADMIN_EMAIL, "name": "RUSHX Admin",
        "picture": "", "role": "admin", "created_at": now_utc().isoformat()}}, upsert=True)
    await db.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"role": "admin"}})


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
