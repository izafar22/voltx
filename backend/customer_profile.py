"""Customer-owned profile and address persistence. Identity writes live in auth flows."""
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pymongo.errors import DuplicateKeyError

try:
    from .auth_service import safe_user
except ImportError:
    from auth_service import safe_user

MAX_ADDRESSES = 20


def failure(status, code, message):
    raise HTTPException(status, {'code': code, 'message': message})


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    @field_validator('*', mode='after')
    @classmethod
    def clean_text(cls, value):
        if isinstance(value, str) and any(ord(c) < 32 for c in value):
            raise ValueError('Control characters are not allowed')
        return value


class NameUpdate(StrictModel):
    name: str = Field(min_length=2, max_length=100)


class Address(StrictModel):
    label: str = Field(min_length=1, max_length=40)
    line1: str = Field(min_length=1, max_length=200)
    line2: str = Field(default='', max_length=200)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    pin: str = Field(pattern=r'^[0-9]{6}$')
    country: Literal['India'] = 'India'


class AddressWrite(Address):
    revision: int = Field(ge=0, strict=True)
    default_pickup: bool = False
    default_delivery: bool = False


class Defaults(StrictModel):
    revision: int = Field(ge=0, strict=True)
    pickup_id: str | None = Field(default=None, max_length=100)
    delivery_id: str | None = Field(default=None, max_length=100)


class AddressDelete(Defaults):
    # Both references are explicit, including when clearing a default.
    pickup_id: str | None = Field(max_length=100)
    delivery_id: str | None = Field(max_length=100)


class ProfileService:
    def __init__(self, auth, db=None):
        self.auth = auth
        self.db = auth.db if db is None else db

    async def document(self, uid):
        return await self.db.customer_profiles.find_one({'_id': uid}) or {
            '_id': uid, 'addresses': [], 'pickup_id': None, 'delivery_id': None, 'revision': 0}

    async def read(self, user):
        doc = await self.document(user['user_id'])
        return {'user': safe_user(user), **{k: doc[k] for k in ('addresses', 'pickup_id', 'delivery_id', 'revision')}}

    async def write(self, uid, revision, doc):
        doc = {**doc, 'revision': revision + 1, 'updated_at': self.auth.clock().isoformat()}
        try:
            result = await self.db.customer_profiles.update_one({'_id': uid, 'revision': revision},
                {'$set': {k: v for k, v in doc.items() if k != '_id'}}, upsert=revision == 0)
        except DuplicateKeyError:
            failure(409, 'stale_profile', 'Your addresses changed. Reload and try again.')
        if not result.matched_count and not result.upserted_id:
            failure(409, 'stale_profile', 'Your addresses changed. Reload and try again.')

    @staticmethod
    def check_defaults(doc):
        ids = {a['id'] for a in doc['addresses']}
        if any(doc[k] is not None and doc[k] not in ids for k in ('pickup_id', 'delivery_id')):
            failure(422, 'invalid_default', 'Choose a saved address or explicitly clear the default.')

    async def save_address(self, user, body, aid=None):
        doc = await self.document(user['user_id'])
        if doc['revision'] != body.revision:
            failure(409, 'stale_profile', 'Your addresses changed. Reload and try again.')
        if aid and not any(a['id'] == aid for a in doc['addresses']):
            failure(404, 'address_not_found', 'Saved address not found.')
        if not aid and len(doc['addresses']) >= MAX_ADDRESSES:
            failure(422, 'address_limit', 'You can save up to 20 addresses.')
        aid = aid or secrets.token_urlsafe(16)
        address = {'id': aid, **body.model_dump(include=set(Address.model_fields))}
        doc['addresses'] = [a for a in doc['addresses'] if a['id'] != aid] + [address]
        for key, selected in (('pickup_id', body.default_pickup), ('delivery_id', body.default_delivery)):
            if selected:
                doc[key] = aid
            elif doc[key] == aid:
                doc[key] = None
        await self.write(user['user_id'], body.revision, doc)

    async def snapshots(self, uid, pickup_id, delivery_id):
        if pickup_id is None and delivery_id is None:
            return {}
        doc = await self.document(uid)
        addresses = {a['id']: a for a in doc['addresses']}
        result = {}
        for kind, aid in (('pickup', pickup_id), ('delivery', delivery_id)):
            if aid is not None:
                if aid not in addresses:
                    failure(422, 'address_not_found', 'A selected address is unavailable. Choose it again.')
                result[kind + '_address'] = dict(addresses[aid])
        return result


def profile_router(resolve_auth):
    router = APIRouter(prefix='/customer')

    async def customer(request: Request, response: Response):
        response.headers['Cache-Control'] = 'no-store'
        auth = resolve_auth()
        user = await auth.authenticate(request)
        if user.get('role') != 'customer':
            failure(403, 'customer_required', 'Customer profile access is required.')
        if request.method != 'GET':
            await auth.limit('profile-write:' + user['user_id'], 60, 60)
        return user

    @router.get('/profile')
    async def read(user=Depends(customer)):
        return await ProfileService(resolve_auth()).read(user)

    @router.patch('/profile')
    async def update(body: NameUpdate, user=Depends(customer)):
        auth = resolve_auth()
        await auth.db.users.update_one({'user_id': user['user_id']}, {'$set': {'name': body.name, 'updated_at': auth.clock().isoformat()}})
        return await ProfileService(auth).read({**user, 'name': body.name})

    @router.post('/addresses')
    async def add(body: AddressWrite, user=Depends(customer)):
        service = ProfileService(resolve_auth())
        await service.save_address(user, body)
        return await service.read(user)

    @router.patch('/addresses/{aid}')
    async def edit(aid: str, body: AddressWrite, user=Depends(customer)):
        service = ProfileService(resolve_auth())
        await service.save_address(user, body, aid)
        return await service.read(user)

    @router.delete('/addresses/{aid}')
    async def delete(aid: str, body: AddressDelete, user=Depends(customer)):
        service = ProfileService(resolve_auth())
        doc = await service.document(user['user_id'])
        if not any(a['id'] == aid for a in doc['addresses']):
            failure(404, 'address_not_found', 'Saved address not found.')
        doc['addresses'] = [a for a in doc['addresses'] if a['id'] != aid]
        doc.update(pickup_id=body.pickup_id, delivery_id=body.delivery_id)
        service.check_defaults(doc)
        await service.write(user['user_id'], body.revision, doc)
        return await service.read(user)

    @router.patch('/address-defaults')
    async def defaults(body: Defaults, user=Depends(customer)):
        service = ProfileService(resolve_auth())
        doc = await service.document(user['user_id'])
        doc.update(pickup_id=body.pickup_id, delivery_id=body.delivery_id)
        service.check_defaults(doc)
        await service.write(user['user_id'], body.revision, doc)
        return await service.read(user)

    return router
