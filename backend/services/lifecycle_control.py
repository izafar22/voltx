"""Operator-only activation control. Inspect is read-only; mutations require explicit confirmation."""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

from .lifecycle_policy import LifecyclePolicy, digest, instruction_preview
from .lifecycle_readiness import missing_indexes, report
from .whatsapp_service import Settings, validate_settings


async def change(db, settings, action, reviewed=False, test_window=0):
    policy = LifecyclePolicy(db, settings)
    if action == "inspect":
        result = await report(db, settings)
        result["pending_jobs"] = await db.whatsapp_jobs.count_documents(
            {"state": {"$in": ["pending", "retryable_failure", "processing"]}}
        )
        return result
    if not reviewed:
        raise ValueError(
            "Explicit operator confirmation of reviewed scope/backlog is required"
        )
    at = datetime.now(timezone.utc)
    previous = await db.whatsapp_control.find_one({"_id": policy.scope_id()})
    if action == "pause":
        result = await db.whatsapp_control.update_one(
            {"_id": policy.scope_id(), "activation_id": settings.activation_id},
            {"$set": {"paused": True, "changed_at": at, "changed_by_uid": os.getuid()}},
        )
        if not result.matched_count:
            raise ValueError("No matching activation to pause")
        return {"paused": True}
    UUID(settings.activation_id)
    validate_settings(settings)
    if not settings.enabled or await missing_indexes(db):
        raise ValueError("Configuration and indexes must be reviewed before activation")
    used_ids = {
        str(UUID(value)) for value in (previous or {}).get("used_activation_ids", [])
    }
    if previous and previous.get("activation_id"):
        used_ids.add(str(UUID(previous["activation_id"])))
    if action == "activate":
        if str(UUID(settings.activation_id)) in used_ids:
            raise ValueError("Retired activation IDs cannot be reused")
        if previous and (
            previous.get("paused") is not True
            or previous.get("activation_id") == settings.activation_id
        ):
            raise ValueError(
                "Pause the previous activation and select a new activation ID first"
            )
    elif action == "resume":
        if (
            not previous
            or previous.get("activation_id") != settings.activation_id
            or previous.get("manifest_digest") != digest(settings.templates)
            or previous.get("instructions_digest")
            != digest(instruction_preview(settings))
            or previous.get("paused") is not True
        ):
            raise ValueError(
                "Resume requires the same paused activation and verified manifest"
            )
    else:
        raise ValueError("Unsupported control action")
    test_until = None
    if settings.mode == "staging":
        if not 1 <= test_window <= 120:
            raise ValueError(
                "Staging activation requires a 1-120 minute authorized window"
            )
        test_until = at + timedelta(minutes=test_window)
    expected = {"_id": policy.scope_id()}
    if previous:
        expected.update(
            activation_id=previous.get("activation_id"),
            paused=previous.get("paused"),
            changed_at=previous.get("changed_at"),
            used_activation_ids=previous.get("used_activation_ids"),
        )
    fields = {
        "activation_id": settings.activation_id,
        "used_activation_ids": sorted(used_ids | {str(UUID(settings.activation_id))}),
        "paused": False,
        "mode": settings.mode,
        "manifest_digest": digest(settings.templates),
        "instructions_digest": digest(instruction_preview(settings)),
        "changed_at": at,
        "changed_by_uid": os.getuid(),
        "test_until": test_until,
    }
    if action == "activate":
        fields.update(activated_at=at, heartbeat_at=None)
    if previous is None:
        try:
            await db.whatsapp_control.insert_one({"_id": policy.scope_id(), **fields})
        except DuplicateKeyError:
            raise ValueError("Activation changed concurrently; inspect again") from None
    else:
        result = await db.whatsapp_control.update_one(expected, {"$set": fields})
        if not result.matched_count:
            raise ValueError("Activation changed concurrently; inspect again")
    return {"active": True, "worker_start_required": True}


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["inspect", "pause", "activate", "resume"],
        nargs="?",
        default="inspect",
    )
    parser.add_argument("--confirm-reviewed-scope-and-backlog", action="store_true")
    parser.add_argument("--test-window-minutes", type=int, default=0)
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    try:
        from ..staging_safety import validate_staging_environment
    except ImportError:
        from staging_safety import validate_staging_environment
    validate_staging_environment()
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], tz_aware=True)
    try:
        result = await change(
            client[os.environ["DB_NAME"]],
            Settings.from_env(),
            args.action,
            args.confirm_reviewed_scope_and_backlog,
            args.test_window_minutes,
        )
        print(json.dumps(result))
        return 0
    except Exception:
        # No exception text: never echo environment values or DB/provider details.
        print(json.dumps({"ok": False, "reason": "control_preflight_or_conflict"}))
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
