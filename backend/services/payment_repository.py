"""Mongo persistence adapter: repair aggregate CAS plus globally unique reference claims."""

from hashlib import sha256
from typing import Protocol
from pymongo.errors import DuplicateKeyError
from fastapi import HTTPException


class PaymentRepository(Protocol):
    async def get(self, repair_id): ...
    async def commit(self, repair, fields, pushes): ...
    async def reserve(self, reference, operation): ...
    async def applied(self, reference): ...


class MongoPaymentRepository:
    def __init__(self, repairs, references):
        self.repairs, self.references = repairs, references

    async def get(self, repair_id):
        return await self.repairs.find_one({"id": repair_id})

    async def commit(self, repair, fields, pushes):
        result = await self.repairs.update_one(
            {
                "id": repair["id"],
                "status": repair["status"],
                "revision": repair.get("revision"),
            },
            {"$set": fields, "$push": pushes, "$inc": {"revision": 1}},
        )
        return bool(result.modified_count)

    @staticmethod
    def reference_key(reference):
        # One RushX merchant ledger. Electronic methods share a namespace to
        # prevent reusing a UPI UTR as a bank-transfer reference on another repair.
        return sha256(reference.encode()).hexdigest()

    async def reserve(self, reference, operation):
        key = self.reference_key(reference)
        # Both transaction identity and operation identity must be unique, even
        # if a request failed after reservation and retries with changed inputs.
        await self.references.create_index(
            [("repair_id", 1), ("receipt.idempotency_key", 1)],
            unique=True,
            name="repair_payment_idempotency",
        )
        try:
            await self.references.insert_one(
                {"_id": key, **operation, "state": "RESERVED"}
            )
            return operation
        except DuplicateKeyError:
            existing = await self.references.find_one(
                {
                    "$or": [
                        {"_id": key},
                        {
                            "repair_id": operation["repair_id"],
                            "receipt.idempotency_key": operation["receipt"][
                                "idempotency_key"
                            ],
                        },
                    ]
                }
            )
            if (existing.get("repair_id"), existing.get("fingerprint")) != (
                operation["repair_id"],
                operation["fingerprint"],
            ):
                raise HTTPException(
                    409,
                    "Transaction reference or idempotency key already reserved or verified",
                ) from None
            return existing

    async def applied(self, reference):
        await self.references.update_one(
            {"_id": self.reference_key(reference)}, {"$set": {"state": "APPLIED"}}
        )
