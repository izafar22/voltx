"""Run separately: python -m services.whatsapp_worker (from backend/)."""

import asyncio
import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from .whatsapp_service import Settings, WhatsAppService


async def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    settings = Settings.from_env()
    if not settings.enabled:
        logging.getLogger(__name__).info("WhatsApp is disabled; worker exiting")
        return
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], tz_aware=True)
    try:
        async with httpx.AsyncClient(follow_redirects=False) as http:
            await WhatsAppService(client[os.environ["DB_NAME"]], settings, http).run()
    finally:
        client.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
