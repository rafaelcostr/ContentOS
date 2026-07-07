"""Production hardening middleware — rate limit + request timeout (V5.5.4)."""

from __future__ import annotations

import asyncio
import os

from contentos_gateway.services.gateway_rate_limiter import (
    gateway_rate_limit_enabled,
    gateway_rate_limit_exempt_paths,
    gateway_rate_limit_per_minute,
    get_gateway_rate_limiter,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def gateway_request_timeout_seconds() -> float:
    try:
        return max(5.0, float(os.getenv("GATEWAY_REQUEST_TIMEOUT_SECONDS", "120")))
    except ValueError:
        return 120.0


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class GatewayHardeningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if gateway_rate_limit_enabled() and path not in gateway_rate_limit_exempt_paths():
            allowed = await get_gateway_rate_limiter().check(
                _client_key(request),
                gateway_rate_limit_per_minute(),
            )
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Gateway rate limit exceeded"},
                    headers={"Retry-After": "60"},
                )

        timeout = gateway_request_timeout_seconds()
        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": f"Request timed out after {timeout:.0f}s"},
            )
