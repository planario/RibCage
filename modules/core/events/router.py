from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from modules.core.config import settings
from modules.core.database import async_session_factory
from modules.core.events.service import emit_event
from modules.core.models import OutboxEvent

router = APIRouter(tags=["events"])

_event_handlers: dict[str, list] = {}


def on_event(event_type: str):
    def decorator(fn):
        _event_handlers.setdefault(event_type, []).append(fn)
        return fn

    return decorator


async def publish_outbox_batch(session, redis_client) -> int:
    result = await session.execute(
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.created_at)
        .limit(100)
    )
    events = result.scalars().all()
    now = datetime.now(timezone.utc)
    for event in events:
        message = {
            "type": event.event_type,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": str(event.aggregate_id),
            "payload": event.payload,
        }
        await redis_client.publish("ribcage:events", json.dumps(message))
        for handler in _event_handlers.get(event.event_type, []):
            await handler(session, message)
        for handler in _event_handlers.get("*", []):
            await handler(session, message)
        event.published_at = now
    return len(events)


async def outbox_publisher_loop() -> None:
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    while True:
        try:
            async with async_session_factory() as session:
                count = await publish_outbox_batch(session, redis_client)
                await session.commit()
            await asyncio.sleep(0.5 if count else 2.0)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(2.0)


@router.get("/stream")
async def stream_events():
    async def event_generator():
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("ribcage:events")
        try:
            yield "data: {\"type\":\"connected\"}\n\n"
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
                if message and message.get("data"):
                    yield f"data: {message['data']}\n\n"
                else:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe("ribcage:events")
            await redis_client.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


__all__ = ["router", "on_event", "outbox_publisher_loop"]
