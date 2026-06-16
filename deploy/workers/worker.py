"""Async workers extracted from monolith (V1)."""

import asyncio
import os

from modules.core.config import settings
from modules.core.database import async_session_factory
from modules.core.events.service import publish_outbox_batch
from modules.core.notification.router import deliver_webhooks
import redis.asyncio as aioredis


async def notification_worker():
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("ribcage:events")
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if message and message.get("data"):
            import json
            data = json.loads(message["data"])
            async with async_session_factory() as session:
                await deliver_webhooks(session, data.get("type", ""), data.get("payload", {}))
                await session.commit()
        await asyncio.sleep(0.1)


async def search_indexer_worker():
    while True:
        async with async_session_factory() as session:
            redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
            await publish_outbox_batch(session, redis_client)
            await session.commit()
        await asyncio.sleep(1)


async def webhook_delivery_worker():
    await notification_worker()


async def digest_worker():
    """Daily digest generation (template-based MVP, LLM optional)."""
    while True:
        await asyncio.sleep(86400)


def main():
    worker_type = os.environ.get("WORKER_TYPE", "search")
    if worker_type == "notification":
        asyncio.run(notification_worker())
    elif worker_type == "webhook":
        asyncio.run(webhook_delivery_worker())
    elif worker_type == "digest":
        asyncio.run(digest_worker())
    else:
        asyncio.run(search_indexer_worker())


if __name__ == "__main__":
    main()
