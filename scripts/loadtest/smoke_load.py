#!/usr/bin/env python3
"""Async smoke load test — no k6 required (V5.5.4)."""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import time

import httpx


async def _worker(
    client: httpx.AsyncClient,
    url: str,
    latencies: list[float],
    errors: list[str],
    stop_at: float,
) -> None:
    while time.monotonic() < stop_at:
        start = time.perf_counter()
        try:
            resp = await client.get(url)
            latencies.append((time.perf_counter() - start) * 1000)
            if resp.status_code >= 500:
                errors.append(f"{resp.status_code}")
        except Exception as exc:
            errors.append(str(exc))
        await asyncio.sleep(0.05)


async def run_load_test(base_url: str, concurrency: int, duration_s: float) -> dict:
    url = f"{base_url.rstrip('/')}/health"
    latencies: list[float] = []
    errors: list[str] = []
    stop_at = time.monotonic() + duration_s
    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        tasks = [
            asyncio.create_task(_worker(client, url, latencies, errors, stop_at))
            for _ in range(concurrency)
        ]
        await asyncio.gather(*tasks)
    total = len(latencies) + len(errors)
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies, default=0)
    return {
        "requests": total,
        "ok": len(latencies),
        "errors": len(errors),
        "error_rate": len(errors) / total if total else 0,
        "p95_ms": round(p95, 1),
        "avg_ms": round(statistics.mean(latencies), 1) if latencies else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ContentOS smoke load test")
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "http://localhost:8000"))
    parser.add_argument("--concurrency", type=int, default=int(os.getenv("LOADTEST_CONCURRENCY", "20")))
    parser.add_argument("--duration", type=float, default=float(os.getenv("LOADTEST_DURATION_SECONDS", "30")))
    parser.add_argument("--max-error-rate", type=float, default=0.05)
    parser.add_argument("--max-p95-ms", type=float, default=800.0)
    args = parser.parse_args()

    result = asyncio.run(run_load_test(args.base_url, args.concurrency, args.duration))
    print(f"requests={result['requests']} ok={result['ok']} errors={result['errors']}")
    print(f"p95={result['p95_ms']}ms avg={result['avg_ms']}ms error_rate={result['error_rate']:.2%}")

    if result["error_rate"] > args.max_error_rate:
        print(f"FAIL: error_rate > {args.max_error_rate:.0%}")
        return 1
    if result["p95_ms"] > args.max_p95_ms:
        print(f"FAIL: p95 {result['p95_ms']}ms > {args.max_p95_ms}ms")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
