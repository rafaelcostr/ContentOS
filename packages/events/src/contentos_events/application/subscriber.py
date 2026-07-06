"""Event subscriber utilities."""

from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator

STREAM_KEY = os.getenv("EVENT_STREAM_KEY", "contentos:stream:events")


class EventSubscriber:
    """Read events from Redis Stream (for replay / debugging)."""

    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url or os.getenv("EVENT_REDIS_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))

    async def read_recent(self, count: int = 50) -> list[dict[str, Any]]:
        import redis.asyncio as aioredis

        client = aioredis.from_url(self.redis_url)
        try:
            entries = await client.xrevrange(STREAM_KEY, count=count)
            events: list[dict[str, Any]] = []
            for entry_id, fields in entries:
                raw = fields.get(b"payload") or fields.get("payload")
                if raw:
                    if isinstance(raw, bytes):
                        raw = raw.decode()
                    data = json.loads(raw)
                    data["stream_id"] = entry_id.decode() if isinstance(entry_id, bytes) else str(entry_id)
                    events.append(data)
            return events
        except Exception:
            return []
        finally:
            await client.aclose()

    async def subscribe_legacy(self) -> AsyncIterator[dict[str, Any]]:
        import redis.asyncio as aioredis

        client = aioredis.from_url(self.redis_url)
        pubsub = client.pubsub()
        await pubsub.subscribe("contentos:events")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    yield json.loads(data)
        finally:
            await pubsub.unsubscribe("contentos:events")
            await client.aclose()
