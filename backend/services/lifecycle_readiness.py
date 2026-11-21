"""Read-only operator preflight: python -m services.lifecycle_readiness. No index writes or sends."""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from .index_contract import equivalent
from .lifecycle_policy import LifecyclePolicy
from .whatsapp_service import Settings, validate_settings

INDEX_PLAN = {
    "whatsapp_jobs": [
        ([("state", 1), ("next_attempt_at", 1)], {}),
        ([("state", 1), ("lease_until", 1)], {}),
        (
            [
                ("activation_id", 1),
                ("repair_id", 1),
                ("source_revision", 1),
                ("state", 1),
            ],
            {},
        ),
    ],
    "whatsapp_receipts": [([("processed", 1), ("next_check_at", 1)], {})],
    "whatsapp_action_inbox": [
        ([("state", 1), ("next_attempt_at", 1)], {}),
        ([("state", 1), ("lease_until", 1)], {}),
    ],
    "repair_requests": [([("whatsapp_outbox._id", 1)], {"sparse": True})],
}


async def missing_indexes(db):
    missing = []
    for collection, plans in INDEX_PLAN.items():
        info = await db[collection].index_information()
        for keys, options in plans:
            if not any(equivalent(index, keys, options) for index in info.values()):
                missing.append(
                    {"collection": collection, "keys": keys, "options": options}
                )
    return missing


async def report(db, settings):
    try:
        validate_settings(settings)
    except Exception:
        return {"ready": False, "reason": "configuration_invalid"}
    if not settings.enabled or not settings.activation_id:
        return {"ready": False, "reason": "lifecycle_disabled"}
    missing = await missing_indexes(db)
    if missing:
        return {
            "ready": False,
            "reason": "indexes_require_review",
            "missing_indexes": missing,
        }
    policy = LifecyclePolicy(db, settings)
    active = bool(await policy.scope())
    return {
        "ready": active,
        "reason": "ready" if active else "activation_unavailable",
        "worker_healthy": bool(await policy.scope(heartbeat=True)),
    }


async def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    try:
        from ..staging_safety import validate_staging_environment
    except ImportError:
        from staging_safety import validate_staging_environment
    validate_staging_environment()
    settings = Settings.from_env()
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], tz_aware=True)
    try:
        result = await report(client[os.environ["DB_NAME"]], settings)
        print(json.dumps(result))
        return 0 if result["ready"] else 1
    except Exception:
        print(json.dumps({"ready": False, "reason": "preflight_unavailable"}))
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
