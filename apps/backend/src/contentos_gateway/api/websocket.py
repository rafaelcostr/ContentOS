import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    import os

    import redis.asyncio as aioredis

    client = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    pubsub = client.pubsub()
    await pubsub.subscribe("contentos:events")

    async def listener():
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])

    task = asyncio.create_task(listener())
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        task.cancel()
        await pubsub.unsubscribe("contentos:events")
        await client.close()
