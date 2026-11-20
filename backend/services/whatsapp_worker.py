"""Run separately: python -m services.whatsapp_worker (from backend/)."""

import asyncio
import logging
import os
import signal
from pathlib import Path

import httpx
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from .whatsapp_service import Settings, WhatsAppService


async def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    try:
        from ..staging_safety import validate_staging_environment
    except ImportError:
        from staging_safety import validate_staging_environment
    validate_staging_environment()
    settings = Settings.from_env()
    if not settings.enabled:
        logging.getLogger(__name__).info("WhatsApp is disabled; worker exiting")
        return
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], tz_aware=True)
    try:
        async with httpx.AsyncClient(follow_redirects=False) as http:
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, stop.set)
            db = client[os.environ["DB_NAME"]]
            from .lifecycle_policy import LifecyclePolicy

            policy = LifecyclePolicy(db, settings)
            from .lifecycle_readiness import report

            if not (await report(db, settings))["ready"]:
                raise RuntimeError("Lifecycle worker readiness failed")

            async def heartbeat():
                while not stop.is_set():
                    try:
                        await db.whatsapp_control.update_one(
                            {
                                "_id": policy.scope_id(),
                                "activation_id": settings.activation_id,
                            },
                            {
                                "$set": {
                                    "heartbeat_at": policy.clock(),
                                    "worker_revision": Path(__file__)
                                    .resolve()
                                    .parents[2]
                                    .name,
                                }
                            },
                        )
                    except Exception:
                        logging.getLogger(__name__).error("lifecycle_heartbeat_failed")
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=15)
                    except asyncio.TimeoutError:
                        pass

            pulse = asyncio.create_task(heartbeat())
            try:
                await WhatsAppService(db, settings, http).run(stop=stop)
            finally:
                stop.set()
                await pulse
    finally:
        client.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
