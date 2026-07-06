"""Prometheus scrape endpoint (Tier E2)."""

from contentos_gateway.services.prometheus_exporter import (
    prometheus_enabled,
    prometheus_metrics_token,
    refresh_prometheus_metrics,
    render_prometheus_metrics,
)
from fastapi import APIRouter, Header, HTTPException, Response, status

router = APIRouter(tags=["Prometheus"])


def _authorize_prometheus(
    authorization: str | None,
    x_prometheus_token: str | None,
) -> None:
    expected = prometheus_metrics_token()
    if not expected:
        return
    token = x_prometheus_token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Prometheus token")


@router.get("/metrics")
async def prometheus_metrics(
    authorization: str | None = Header(None),
    x_prometheus_token: str | None = Header(None, alias="X-Prometheus-Token"),
) -> Response:
    if not prometheus_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prometheus metrics disabled")
    _authorize_prometheus(authorization, x_prometheus_token)

    from contentos_database.session import _session_factory

    if _session_factory is not None:
        async with _session_factory() as db:
            await refresh_prometheus_metrics(db)
    else:
        await refresh_prometheus_metrics(None)

    body, content_type = render_prometheus_metrics()
    return Response(content=body, media_type=content_type)
