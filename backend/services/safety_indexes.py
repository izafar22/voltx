"""Non-destructive startup indexes. Duplicate legacy data fails startup for review."""
from .index_contract import SAFETY_INDEXES, ensure_index


async def initialize_safety_indexes(db):
    for collection, keys, options in SAFETY_INDEXES:
        await ensure_index(db, collection, keys, options)
