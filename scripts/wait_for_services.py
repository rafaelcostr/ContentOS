"""Wait until ContentOS stack and AI providers are healthy."""

import asyncio
import os
import sys
import time

import httpx

GATEWAY = os.getenv("GATEWAY_URL", "http://localhost:8000")
OLLAMA = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
PIPER = os.getenv("PIPER_URL", "http://localhost:5000")
WHISPER = os.getenv("WHISPER_URL", "http://localhost:8080")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
TIMEOUT = int(os.getenv("WAIT_TIMEOUT_SECONDS", "900"))
INTERVAL = int(os.getenv("WAIT_INTERVAL_SECONDS", "10"))


async def _check(name: str, url: str, fn) -> bool:
    try:
        ok = await fn()
        status = "OK" if ok else "WAIT"
        print(f"  [{status}] {name} — {url}")
        return ok
    except Exception as exc:
        print(f"  [WAIT] {name} — {exc}")
        return False


async def check_gateway(client: httpx.AsyncClient) -> bool:
    r = await client.get(f"{GATEWAY}/health")
    return r.status_code == 200


async def check_ollama(client: httpx.AsyncClient) -> bool:
    r = await client.get(f"{OLLAMA}/api/tags")
    if r.status_code != 200:
        return False
    models = r.json().get("models", [])
    base = OLLAMA_MODEL.split(":")[0]
    return any(base in m.get("name", "") for m in models)


async def check_piper(client: httpx.AsyncClient) -> bool:
    r = await client.get(f"{PIPER}/health")
    if r.status_code != 200:
        return False
    data = r.json()
    return data.get("status") == "ok" and data.get("model_ready", False)


async def check_whisper(client: httpx.AsyncClient) -> bool:
    r = await client.get(f"{WHISPER}/health")
    if r.status_code != 200:
        return False
    return r.json().get("loaded", False)


async def check_providers_api(client: httpx.AsyncClient) -> bool:
    r = await client.get(f"{GATEWAY}/api/v1/providers/health")
    if r.status_code != 200:
        return False
    return r.json().get("all_healthy", False)


CHECKS = [
    ("Gateway", GATEWAY, check_gateway),
    ("Ollama", OLLAMA, check_ollama),
    ("Piper", PIPER, check_piper),
    ("Whisper", WHISPER, check_whisper),
    ("Providers API", GATEWAY, check_providers_api),
]


async def main() -> int:
    print(f"Waiting for ContentOS stack (timeout {TIMEOUT}s)...")
    deadline = time.monotonic() + TIMEOUT

    async with httpx.AsyncClient(timeout=15.0) as client:
        while time.monotonic() < deadline:
            print(f"\n--- {time.strftime('%H:%M:%S')} ---")
            results = []
            for name, url, fn in CHECKS:
                results.append(await _check(name, url, lambda f=fn: f(client)))
            if all(results):
                print("\nAll services healthy.")
                return 0
            await asyncio.sleep(INTERVAL)

    print("\nTimeout — not all services became healthy.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
