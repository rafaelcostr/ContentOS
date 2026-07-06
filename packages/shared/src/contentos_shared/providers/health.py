"""Health checks for external AI provider services."""

import os
import time
from dataclasses import dataclass

import httpx

_health_cache: tuple[float, list["ProviderHealthResult"]] | None = None
HEALTH_CACHE_TTL = 30.0


@dataclass
class ProviderHealthResult:
    name: str
    url: str
    healthy: bool
    detail: str = ""


async def check_ollama() -> ProviderHealthResult:
    base = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base}/api/tags")
            resp.raise_for_status()
            tags = resp.json().get("models", [])
            names = [m.get("name", "").split(":")[0] for m in tags]
            model_base = model.split(":")[0]
            if any(model_base in n or n in model for n in names):
                return ProviderHealthResult("ollama", base, True, f"model {model} available")
            return ProviderHealthResult("ollama", base, False, f"model {model} not pulled yet")
    except Exception as exc:
        return ProviderHealthResult("ollama", base, False, str(exc))


async def check_piper() -> ProviderHealthResult:
    base = os.getenv("PIPER_URL", "http://piper:5000").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base}/health")
            resp.raise_for_status()
            data = resp.json()
            ready = data.get("status") == "ok" and data.get("model_ready", False)
            return ProviderHealthResult("piper", base, ready, data.get("voice", ""))
    except Exception as exc:
        return ProviderHealthResult("piper", base, False, str(exc))


async def check_whisper() -> ProviderHealthResult:
    base = os.getenv("WHISPER_URL", "http://whisper:8080").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base}/health")
            resp.raise_for_status()
            data = resp.json()
            ready = data.get("loaded", False)
            return ProviderHealthResult("whisper", base, ready, data.get("model", ""))
    except Exception as exc:
        return ProviderHealthResult("whisper", base, False, str(exc))


async def check_all_providers() -> list[ProviderHealthResult]:
    global _health_cache
    now = time.monotonic()
    if _health_cache and now - _health_cache[0] < HEALTH_CACHE_TTL:
        return _health_cache[1]

    import asyncio

    results = list(await asyncio.gather(check_ollama(), check_piper(), check_whisper()))
    _health_cache = (now, results)
    return results
