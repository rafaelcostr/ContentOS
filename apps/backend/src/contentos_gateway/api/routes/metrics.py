"""Infrastructure and system metrics API."""

from contentos_database.models import User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.metrics_collector import (
    collect_celery_queues,
    collect_postgres_metrics,
    collect_redis_metrics,
    collect_system_metrics,
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/metrics", tags=["Metrics"])


class CpuResponse(BaseModel):
    percent: float
    cores: int


class MemoryResponse(BaseModel):
    used_mb: float
    total_mb: float
    percent: float


class DiskResponse(BaseModel):
    used_gb: float
    total_gb: float
    percent: float


class GpuResponse(BaseModel):
    available: bool
    name: str = ""
    utilization: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0


class SystemMetricsResponse(BaseModel):
    cpu: CpuResponse
    memory: MemoryResponse
    disk: DiskResponse
    gpu: GpuResponse | None = None


class InfrastructureResponse(BaseModel):
    redis: dict
    postgres: dict
    celery: dict


@router.get("/system", response_model=SystemMetricsResponse)
async def system_metrics(_user: User = Depends(get_current_user)) -> SystemMetricsResponse:
    m = collect_system_metrics()
    gpu = None
    if m.gpu:
        gpu = GpuResponse(
            available=m.gpu.available,
            name=m.gpu.name,
            utilization=m.gpu.utilization,
            memory_used_mb=m.gpu.memory_used_mb,
            memory_total_mb=m.gpu.memory_total_mb,
        )
    return SystemMetricsResponse(
        cpu=CpuResponse(percent=m.cpu.percent, cores=m.cpu.cores),
        memory=MemoryResponse(used_mb=m.memory.used_mb, total_mb=m.memory.total_mb, percent=m.memory.percent),
        disk=DiskResponse(used_gb=m.disk.used_gb, total_gb=m.disk.total_gb, percent=m.disk.percent),
        gpu=gpu,
    )


@router.get("/infrastructure", response_model=InfrastructureResponse)
async def infrastructure_metrics(
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> InfrastructureResponse:
    redis_m = await collect_redis_metrics()
    postgres_m = await collect_postgres_metrics(db)
    celery_m = await collect_celery_queues()
    return InfrastructureResponse(redis=redis_m, postgres=postgres_m, celery=celery_m)
