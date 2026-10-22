"""Non-destructive startup indexes. Duplicate legacy data fails startup for review."""


async def initialize_safety_indexes(db):
    await db.payment_references.create_index(
        [("repair_id", 1), ("receipt.idempotency_key", 1)],
        unique=True,
        name="repair_payment_idempotency",
    )
    await db.repair_requests.create_index("creation_key", unique=True, sparse=True)
    for prefix in ([], [("user_id", 1)], [("charger_id", 1)], [("status", 1)]):
        await db.repair_requests.create_index(prefix + [("created_at", -1), ("id", -1)])
