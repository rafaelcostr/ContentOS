"""Redis Streams transport."""

from __future__ import annotations

import json
import os
from typing import Any

STREAM_KEY = os.getenv("EVENT_STREAM_KEY", "contentos:stream:events")
STREAM_MAXLEN = int(os.getenv("EVENT_STREAM_MAXLEN", "10000"))


class RedisStreamTransport:
    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url or os.getenv("EVENT_REDIS_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))

    async def append(self, payload: dict[str, Any]) -> str | None:
        import redis.asyncio as aioredis

        client = aioredis.from_url(self.redis_url)
        try:
            event_id = await client.xadd(
                STREAM_KEY,
                {"payload": json.dumps(payload, default=str)},
                maxlen=STREAM_MAXLEN,
                approximate=True,
            )
            return str(event_id)
        finally:
            await client.aclose()

    def append_sync(self, payload: dict[str, Any]) -> str | None:
        import redis

        client = redis.from_url(self.redis_url)
        try:
            event_id = client.xadd(
                STREAM_KEY,
                {"payload": json.dumps(payload, default=str)},
                maxlen=STREAM_MAXLEN,
                approximate=True,
            )
            return str(event_id)
        finally:
            client.close()

    async def publish_legacy(self, payload: dict[str, Any]) -> None:
        import redis.asyncio as aioredis

        client = aioredis.from_url(self.redis_url)
        try:
            await client.publish("contentos:events", json.dumps(payload, default=str))
        finally:
            await client.aclose()

    def publish_legacy_sync(self, payload: dict[str, Any]) -> None:
        import redis

        client = redis.from_url(self.redis_url)
        try:
            client.publish("contentos:events", json.dumps(payload, default=str))
        finally:
            client.close()

    async def stream_info(self) -> dict[str, Any]:
        import redis.asyncio as aioredis

        client = aioredis.from_url(self.redis_url)
        try:
            info = await client.xinfo_stream(STREAM_KEY)
            return {
                "stream_key": STREAM_KEY,
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
            }
        except Exception as exc:
            return {"stream_key": STREAM_KEY, "length": 0, "error": str(exc)}
        finally:
            await client.aclose()
