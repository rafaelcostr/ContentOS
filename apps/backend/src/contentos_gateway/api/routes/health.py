from contentos_database.session import get_session
from contentos_gateway.services.metrics_collector import collect_postgres_metrics, collect_redis_metrics
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "contentos-gateway"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_session)):
    """Readiness — DB + Redis must be healthy (K8s production probe)."""
    redis_m = await collect_redis_metrics()
    postgres_m = await collect_postgres_metrics(db)
    redis_ok = redis_m.get("status") == "healthy"
    postgres_ok = postgres_m.get("status") == "healthy"
    if not redis_ok or not postgres_ok:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "redis": redis_m.get("status", "unknown"),
                "postgres": postgres_m.get("status", "unknown"),
            },
        )
    return {
        "status": "ready",
        "service": "contentos-gateway",
        "redis": "healthy",
        "postgres": "healthy",
        "postgres_latency_ms": postgres_m.get("latency_ms"),
    }
