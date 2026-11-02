"""Customer lifecycle and shared owner/admin sessions; no SMS delivery is simulated in provider mode."""
import hashlib
import hmac
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, OperationFailure


def normalize_phone(value):
    if not isinstance(value, str) or not re.fullmatch(r"\+?[0-9\s()-]+", value.strip()):
        raise HTTPException(422, "Enter a valid Indian mobile number")
    digits = re.sub(r"[\s()-]", "", value.strip()).removeprefix("+")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if not re.fullmatch(r"[6-9][0-9]{9}", digits):
        raise HTTPException(422, "Enter a valid Indian mobile number")
    return "+91" + digits


def utcnow():
    return datetime.now(timezone.utc)


def safe_user(user):
    result = {key: user.get(key, default) for key, default in {
        "user_id": "", "name": "", "phone": "", "email": "", "role": "customer",
        "status": "active", "onboarding_completed": True,
    }.items()}
    result["phone_verified"] = bool(user.get("phone_verified_at"))
    return result


@dataclass(frozen=True)
class AuthSettings:
    secret: str
    environment: str = "production"
    otp_mode: str = "provider"
    expose_demo: bool = False
    origins: tuple = ("http://localhost:3000",)
    session_seconds: int = 86400

    @classmethod
    def from_env(cls):
        environment = os.getenv("APP_ENV", "production")
        origins = tuple(x.strip().rstrip("/") for x in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if x.strip())
        return cls(os.environ["JWT_SECRET"], environment, os.getenv("OTP_MODE", "provider"),
                   os.getenv("EXPOSE_DEMO_OTP", "false").lower() == "true", origins)

    def validate(self):
        if self.environment not in ("production", "development", "test"):
            raise RuntimeError("APP_ENV must be production, development, or test")
        if self.otp_mode not in ("demo", "provider"):
            raise RuntimeError("OTP_MODE must be demo or provider")
        if not self.origins or any(not re.fullmatch(r"https?://[^/]+", origin) or "*" in origin for origin in self.origins):
            raise RuntimeError("Configure explicit CORS_ORIGINS without wildcards")
        if self.environment == "production":
            if self.otp_mode == "demo" or self.expose_demo:
                raise RuntimeError("Demo OTP is forbidden in production")
            if len(self.secret) < 32 or any(not origin.startswith("https://") for origin in self.origins):
                raise RuntimeError("Production requires a strong JWT_SECRET and HTTPS frontend origins")


class OtpProvider(Protocol):
    async def send_otp(self, phone: str, code: str): ...


class DemoOtpProvider:
    async def send_otp(self, phone, code):
        # Deliberately no logs, network calls, or claims of SMS delivery.
        return None


class UnconfiguredOtpProvider:
    async def send_otp(self, phone, code):
        raise HTTPException(503, "SMS delivery is not configured")


class PhoneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone: str = Field(max_length=40)


class VerifyRequest(PhoneRequest):
    challenge_id: str = Field(min_length=1, max_length=100)
    otp: str = Field(pattern=r"^[0-9]{6}$")


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(default="", max_length=254)


class AuthService:
    def __init__(self, db, settings, provider=None, clock=utcnow):
        self.db, self.settings, self.clock = db, settings, clock
        settings.validate()
        try:
            from .google_oidc import GoogleOIDC
        except ImportError:
            from google_oidc import GoogleOIDC
        self.google = GoogleOIDC(self)
        self.provider = provider or self.configured_provider()

    def configured_provider(self):
        if self.settings.otp_mode == "demo":
            return DemoOtpProvider()
        if os.getenv("SMS_PROVIDER", "").lower() == "msg91":
            try:
                try:
                    from .sms_provider import Msg91OtpProvider, Msg91Settings
                except ImportError:
                    from sms_provider import Msg91OtpProvider, Msg91Settings
                return Msg91OtpProvider(Msg91Settings.from_env())
            except ValueError:
                pass
        return UnconfiguredOtpProvider()

    @staticmethod
    def challenge_scope(purpose="login", user_id=None):
        if purpose == "login":
            return {"purpose": {"$in": ["login", None]}}
        return {"purpose": "link_phone", "user_id": user_id}


    def digest(self, value):
        return hmac.new(self.settings.secret.encode(), value.encode(), hashlib.sha256).hexdigest()

    async def initialize(self):
        # Audit all normalized identities BEFORE changing any existing phone values.
        seen, changes = {}, []
        async for user in self.db.users.find({}, {"phone": 1, "user_id": 1}):
            try:
                normalized = normalize_phone(user.get("phone"))
            except HTTPException:
                # Preserve malformed historical fixtures for explicit operator repair.
                continue
            if normalized in seen:
                raise RuntimeError("Phone normalization collision: resolve duplicate users before auth startup; no accounts were merged")
            seen[normalized] = user["_id"]
            if normalized != user["phone"]:
                changes.append((user["_id"], user["phone"], normalized))
        try:
            # Build replacement before removing legacy full indexes; no uniqueness gap.
            partial = {"phone": {"$type": "string"}}
            await self.db.users.create_index("phone", unique=True, name="auth_phone_partial_unique", partialFilterExpression=partial)
            indexes = await self.db.users.index_information()
            for name, spec in indexes.items():
                if spec.get("key") == [("phone", 1)] and not spec.get("partialFilterExpression"):
                    if not spec.get("unique"):
                        continue
                    await self.db.users.drop_index(name)
            await self.db.users.create_index([("auth_provider", 1), ("auth_subject", 1)], unique=True,
                name="auth_provider_subject_unique", partialFilterExpression={"auth_provider": {"$type": "string"}, "auth_subject": {"$type": "string"}})
            await self.db.users.create_index("user_id", unique=True, name="auth_user_id_unique")
            await self.db.wallets.create_index("user_id", unique=True, name="auth_wallet_user_unique")
            for uid, old, phone in changes:
                await self.db.users.update_one({"_id": uid, "phone": old}, {"$set": {"phone": phone}})
            for collection in (self.db.auth_challenges, self.db.auth_limits, self.db.auth_sessions, self.db.auth_registrations, self.db.auth_google_transactions):
                await collection.create_index("expires_at", expireAfterSeconds=0)
            await self.db.auth_challenges.create_index("phone")
        except OperationFailure:
            raise RuntimeError("Auth index initialization failed; audit existing duplicate/index conflicts without deleting customer data") from None

    async def limit(self, key, maximum, seconds):
        now = self.clock()
        bucket = int(now.timestamp()) // seconds
        identity = self.digest(f"{key}:{bucket}")
        try:
            await self.db.auth_limits.update_one({"_id": identity, "count": {"$lt": maximum}},
                {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": now + timedelta(seconds=seconds * 2)}}, upsert=True)
        except DuplicateKeyError:
            raise HTTPException(429, "Too many requests. Try again later.", headers={"Retry-After": str(seconds)}) from None

    async def request_otp(self, phone: str, ip: str | None, purpose="login", user_id=None):
        ip = ip or "unknown"
        phone = normalize_phone(phone)

        if isinstance(self.provider, UnconfiguredOtpProvider):
            raise HTTPException(503, "SMS delivery is not configured")

        now = self.clock()

        # Maximum 30 OTP requests per IP per hour
        await self.limit("ip:" + ip, 30, 3600)

        # Maximum 5 OTP requests per phone number per hour
        await self.limit("phone:" + phone, 5, 3600)

        try:
            await self.db.auth_limits.update_one(
                {
                    "_id": self.digest("cooldown:" + phone),
                    "next_at": {"$lte": now},
                },
                {
                    "$set": {
                        "next_at": now + timedelta(seconds=60),
                        "expires_at": now + timedelta(hours=1),
                    }
                },
                upsert=True,
            )
        except DuplicateKeyError:
            raise HTTPException(
                429,
                "Please wait before requesting another code.",
                headers={"Retry-After": "60"},
            ) from None

        cid = secrets.token_urlsafe(24)

        code = (
            "123456"
            if self.settings.otp_mode == "demo"
            else f"{secrets.randbelow(1000000):06d}"
        )

        await self.db.auth_challenges.update_many(
            {
                "phone": phone,
                **self.challenge_scope(purpose, user_id),
                "consumed": False,
            },
            {
                "$set": {
                    "consumed": True
                }
            },
        )

        await self.db.auth_challenges.insert_one(
            {
                "_id": cid,
                "phone": phone,
                "purpose": purpose,
                "user_id": user_id,
                "otp_hash": self.digest(f"{cid}:{phone}:{code}"),
                "created_at": now,
                "expires_at": now + timedelta(minutes=5),
                "attempts": 0,
                "consumed": False,
                "delivered": False,
            }
        )

        try:
            await self.provider.send_otp(phone, code)
        except Exception:
            await self.db.auth_challenges.update_one(
                {"_id": cid},
                {"$set": {"consumed": True}},
            )

            raise HTTPException(
                503,
                "Unable to deliver code. Please try again later.",
            ) from None

        await self.db.auth_challenges.update_one(
            {"_id": cid},
            {"$set": {"delivered": True}},
        )

        result = {
            "ok": True,
            "challenge_id": cid,
            "expires_in": 300,
            "resend_after": 60,
        }

        if self.settings.otp_mode == "demo" and self.settings.expose_demo:
            result["demo_otp"] = code

        return result

    async def consume_otp(self, cid, phone, code, purpose="login", user_id=None):
        phone, now = normalize_phone(phone), self.clock()
        scope = self.challenge_scope(purpose, user_id)
        challenge = await self.db.auth_challenges.find_one_and_update({"_id": cid, "phone": phone, **scope,
            "consumed": False, "delivered": True, "expires_at": {"$gt": now}, "attempts": {"$lt": 5}},
            {"$inc": {"attempts": 1}}, return_document=ReturnDocument.BEFORE)
        if not challenge:
            old = await self.db.auth_challenges.find_one({"_id": cid, "phone": phone, **scope})
            if old and old.get("attempts", 0) >= 5:
                raise HTTPException(429, "Too many attempts. Request a new code.")
            raise HTTPException(400, "Code expired or already used. Request a new code.")
        if not hmac.compare_digest(challenge["otp_hash"], self.digest(f"{cid}:{phone}:{code}")):
            if challenge["attempts"] >= 4:
                raise HTTPException(429, "Too many attempts. Request a new code.")
            raise HTTPException(400, "Incorrect code. Please try again.")
        consumed = await self.db.auth_challenges.update_one({"_id": cid, "consumed": False, "expires_at": {"$gt": now}}, {"$set": {"consumed": True}})
        if not consumed.modified_count:
            raise HTTPException(400, "Code expired or already used. Request a new code.")
        return phone

    async def verify(self, cid, phone, code):
        phone = await self.consume_otp(cid, phone, code)
        user = await self.db.users.find_one({"phone": phone})
        if user:
            self.ensure_active(user)
            verified_at = self.clock().isoformat()
            user = await self.db.users.find_one_and_update(
                {"user_id": user["user_id"], "phone": phone, "status": user.get("status")},
                {"$set": {"phone_verified_at": verified_at}}, return_document=ReturnDocument.AFTER)
            if not user:
                raise HTTPException(409, "Your account changed. Please sign in again.")
            self.ensure_active(user)
            return user, None
        rid = secrets.token_urlsafe(24)
        expires = self.clock() + timedelta(minutes=10)
        await self.db.auth_registrations.insert_one({"_id": rid, "phone": phone, "expires_at": expires})
        return None, jwt.encode({"sub": phone, "jti": rid, "purpose": "registration", "exp": expires}, self.settings.secret, algorithm="HS256")

    @staticmethod
    def ensure_active(user):
        if user.get("status", "active") != "active":
            raise HTTPException(403, "This account is unavailable. Contact support.")

    def decode(self, token, purpose):
        try:
            data = jwt.decode(token, self.settings.secret, algorithms=["HS256"], options={"require": ["exp", "sub", "jti", "purpose"]})
            if data["purpose"] != purpose:
                raise jwt.InvalidTokenError()
            return data
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Your verification or session expired. Please sign in again.") from None

    async def register(self, token, name, email):
        data = self.decode(token, "registration")
        name, email = name.strip(), email.strip()
        if not 2 <= len(name) <= 100 or any(ord(c) < 32 for c in name):
            raise HTTPException(422, "Enter your full name (2–100 characters).")
        if email and (len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)):
            raise HTTPException(422, "Enter a valid email address.")
        grant = await self.db.auth_registrations.find_one({"_id": data["jti"], "phone": data["sub"], "expires_at": {"$gt": self.clock()}})
        if not grant:
            raise HTTPException(401, "Phone verification expired. Please sign in again.")
        # Deterministic identity for concurrent requests using the same grant. A phone
        # unique index also handles two independently issued registration grants.
        user_id = "user_" + self.digest("registration:" + data["jti"])[:24]
        now = self.clock().isoformat()
        document = {"user_id": user_id, "phone": data["sub"], "role": "customer", "name": name,
            "email": email, "status": "active", "onboarding_completed": True, "phone_verified_at": now, "created_at": now, "updated_at": now}
        try:
            await self.db.users.update_one({"phone": data["sub"]}, {"$setOnInsert": document}, upsert=True)
        except DuplicateKeyError:
            pass
        user = await self.db.users.find_one({"phone": data["sub"]})
        # Never turn a raced owner/admin account into a customer or authenticate it
        # with an old registration grant.
        if user["user_id"] != user_id or user["role"] != "customer":
            raise HTTPException(409, "An account already exists. Please sign in.")
        self.ensure_active(user)
        await self.db.wallets.update_one({"user_id": user_id}, {"$setOnInsert": {"balance": 0.0}}, upsert=True)
        used = await self.db.auth_registrations.delete_one({"_id": data["jti"]})
        if not used.deleted_count:
            raise HTTPException(409, "Registration already completed. Please sign in.")
        return user

    @staticmethod
    def ensure_linkable(user):
        if user.get("role") != "customer" or (user.get("auth_provider") != "google" and not user.get("phone")):
            raise HTTPException(403, "Phone verification is available for customer accounts.")
        if user.get("phone_verified_at"):
            raise HTTPException(409, "A verified phone is already linked. Contact RushX support to change it.")

    @staticmethod
    def ensure_phone_target(user, phone):
        # Historical SMS sessions can prove their already assigned number, but
        # this endpoint cannot change that identity to a different phone.
        if user.get("auth_provider") != "google" and normalize_phone(phone) != normalize_phone(user.get("phone")):
            raise HTTPException(403, "Verify your existing account number or contact RushX support.")

    async def request_phone_link(self, user, phone, ip):
        self.ensure_linkable(user)
        self.ensure_phone_target(user, phone)
        return await self.request_otp(phone, ip, "link_phone", user["user_id"])

    async def verify_phone_link(self, user, cid, phone, code):
        self.ensure_linkable(user)
        self.ensure_phone_target(user, phone)
        phone = await self.consume_otp(cid, phone, code, "link_phone", user["user_id"])
        try:
            updated = await self.db.users.find_one_and_update({
                "user_id": user["user_id"], "role": "customer", "auth_provider": user.get("auth_provider"),
                "phone": user.get("phone"), "phone_verified_at": user.get("phone_verified_at"), "status": user.get("status"),
            }, {"$set": {"phone": phone, "phone_verified_at": self.clock().isoformat(),
                         "updated_at": self.clock().isoformat()}}, return_document=ReturnDocument.AFTER)
        except DuplicateKeyError:
            raise HTTPException(409, "This number is already linked to another account. Sign in with that number or contact RushX support for account recovery.") from None
        if not updated:
            raise HTTPException(409, "Your profile changed. Refresh and try again.")
        return safe_user(updated)

    async def authenticate(self, request):
        # Legacy stateless bearer tokens deliberately expire at migration. No role is
        # trusted from the browser: every request checks the stored user and session.
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(401, "Not authenticated")
        data = self.decode(token, "session")
        session = await self.db.auth_sessions.find_one({"_id": data["jti"], "user_id": data["sub"], "expires_at": {"$gt": self.clock()}})
        if not session:
            raise HTTPException(401, "Session expired. Please sign in again.")
        user = await self.db.users.find_one({"user_id": data["sub"]})
        if not user:
            raise HTTPException(401, "Not authenticated")
        self.ensure_active(user)
        return user

    async def login_response(self, user, response, request):
        self.ensure_active(user)
        await self.revoke(request)
        sid = secrets.token_urlsafe(24)
        expires = self.clock() + timedelta(seconds=self.settings.session_seconds)
        await self.db.auth_sessions.insert_one({"_id": sid, "user_id": user["user_id"], "expires_at": expires})
        token = jwt.encode({"sub": user["user_id"], "role": user["role"], "jti": sid, "purpose": "session", "exp": expires}, self.settings.secret, algorithm="HS256")
        response.set_cookie("access_token", token, max_age=self.settings.session_seconds, httponly=True,
            secure=self.settings.environment == "production", samesite="lax", path="/")
        response.headers["Cache-Control"] = "no-store"
        return {"authenticated": True, "registration_required": False, "user": safe_user(user)}

    async def revoke(self, request):
        token = request.cookies.get("access_token")
        if token:
            try:
                data = self.decode(token, "session")
                await self.db.auth_sessions.delete_one({"_id": data["jti"]})
            except HTTPException:
                pass


def auth_router(service):
    router = APIRouter(prefix="/auth")

    @router.get("/google/login")
    async def google_login(request: Request):
        return await service.google.login(request)

    @router.get("/google/callback")
    async def google_callback(request: Request):
        return await service.google.callback(request)

    @router.post("/phone/request-otp")
    async def request_phone(body: PhoneRequest, request: Request):
        user = await service.authenticate(request)
        return await service.request_phone_link(user, body.phone, request.client.host if request.client else None)

    @router.post("/phone/verify-otp")
    async def verify_phone(body: VerifyRequest, request: Request):
        user = await service.authenticate(request)
        return {"user": await service.verify_phone_link(user, body.challenge_id, body.phone, body.otp)}

    @router.post("/request-otp")
    async def request_otp(body: PhoneRequest, request: Request):
        client_ip = (
            request.client.host
            if request.client and request.client.host
            else "unknown"
        )

        return await service.request_otp(body.phone, client_ip)

    @router.post("/verify-otp")
    async def verify(body: VerifyRequest, request: Request, response: Response):
        user, token = await service.verify(body.challenge_id, body.phone, body.otp)
        if user:
            return await service.login_response(user, response, request)
        response.headers["Cache-Control"] = "no-store"
        return {"authenticated": False, "registration_required": True, "registration_token": token}

    @router.post("/register-customer")
    async def register(body: RegistrationRequest, request: Request, response: Response):
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Phone verification is required.")
        user = await service.register(authorization[7:], body.name, body.email)
        return await service.login_response(user, response, request)

    @router.get("/me")
    async def me(request: Request, response: Response):
        response.headers["Cache-Control"] = "no-store"
        return safe_user(await service.authenticate(request))

    @router.post("/logout")
    async def logout(request: Request, response: Response):
        await service.revoke(request)
        response.delete_cookie("access_token", path="/", httponly=True, secure=service.settings.environment == "production", samesite="lax")
        return {"ok": True}

    return router
