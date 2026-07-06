"""Event Bus publisher — Redis Streams + pub/sub + PostgreSQL."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from contentos_events.domain.event import DomainEvent
from contentos_events.infrastructure.event_store import store_sync
from contentos_events.infrastructure.redis_streams import RedisStreamTransport


class EventBusPublisher:
    """Publishes domain events to stream, legacy pub/sub, and event store."""

    def __init__(self, transport: RedisStreamTransport | None = None) -> None:
        self._transport = transport or RedisStreamTransport()

    async def publish(self, event: Any) -> None:
        domain = event if isinstance(event, DomainEvent) else DomainEvent.from_workflow_event(event)
        payload = domain.to_dict()
        await self._transport.append(payload)
        await self._transport.publish_legacy(payload)
        store_sync(payload)

    def publish_sync(self, event: Any) -> None:
        domain = event if isinstance(event, DomainEvent) else DomainEvent.from_workflow_event(event)
        payload = domain.to_dict()
        self._transport.append_sync(payload)
        self._transport.publish_legacy_sync(payload)
        store_sync(payload)

    async def stream_info(self) -> dict[str, Any]:
        return await self._transport.stream_info()


@lru_cache(maxsize=1)
def get_event_bus() -> EventBusPublisher:
    return EventBusPublisher()
