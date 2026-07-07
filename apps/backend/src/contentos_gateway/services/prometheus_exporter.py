"""Prometheus metrics exporter (Tier E2)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from contentos_gateway.services.metrics_collector import (
    AGENT_QUEUES,
    collect_celery_queues,
    collect_postgres_metrics,
    collect_redis_metrics,
    collect_system_metrics,
)
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Gauge, Info, generate_latest
from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

REGISTRY = CollectorRegistry()

BUILD_INFO = Info("contentos_build", "ContentOS build metadata", registry=REGISTRY)

CPU_PERCENT = Gauge("contentos_cpu_percent", "CPU utilization percent", registry=REGISTRY)
CPU_CORES = Gauge("contentos_cpu_cores", "Number of CPU cores", registry=REGISTRY)
MEMORY_USED_BYTES = Gauge("contentos_memory_used_bytes", "Used memory in bytes", registry=REGISTRY)
MEMORY_TOTAL_BYTES = Gauge("contentos_memory_total_bytes", "Total memory in bytes", registry=REGISTRY)
MEMORY_PERCENT = Gauge("contentos_memory_percent", "Memory utilization percent", registry=REGISTRY)
DISK_USED_BYTES = Gauge("contentos_disk_used_bytes", "Used disk space in bytes", registry=REGISTRY)
DISK_TOTAL_BYTES = Gauge("contentos_disk_total_bytes", "Total disk space in bytes", registry=REGISTRY)
DISK_PERCENT = Gauge("contentos_disk_percent", "Disk utilization percent", registry=REGISTRY)
GPU_UTILIZATION = Gauge("contentos_gpu_utilization_percent", "GPU utilization percent", registry=REGISTRY)
GPU_MEMORY_USED_BYTES = Gauge("contentos_gpu_memory_used_bytes", "GPU memory used in bytes", registry=REGISTRY)
GPU_MEMORY_TOTAL_BYTES = Gauge("contentos_gpu_memory_total_bytes", "GPU memory total in bytes", registry=REGISTRY)

REDIS_UP = Gauge("contentos_redis_up", "Redis availability (1=up)", registry=REGISTRY)
REDIS_MEMORY_BYTES = Gauge("contentos_redis_memory_bytes", "Redis used memory in bytes", registry=REGISTRY)
REDIS_CONNECTED_CLIENTS = Gauge("contentos_redis_connected_clients", "Redis connected clients", registry=REGISTRY)

POSTGRES_UP = Gauge("contentos_postgres_up", "PostgreSQL availability (1=up)", registry=REGISTRY)
POSTGRES_LATENCY_SECONDS = Gauge(
    "contentos_postgres_latency_seconds",
    "PostgreSQL round-trip latency in seconds",
    registry=REGISTRY,
)

CELERY_WORKERS = Gauge("contentos_celery_workers", "Active Celery workers", registry=REGISTRY)
CELERY_QUEUE_DEPTH = Gauge(
    "contentos_celery_queue_depth",
    "Pending tasks per Celery queue",
    ["queue"],
    registry=REGISTRY,
)
CELERY_PENDING_TOTAL = Gauge("contentos_celery_pending_total", "Total pending Celery tasks", registry=REGISTRY)

PIPELINES_TOTAL = Gauge(
    "contentos_pipelines_total",
    "Pipelines by status",
    ["status"],
    registry=REGISTRY,
)
JOBS_TOTAL = Gauge(
    "contentos_jobs_total",
    "Jobs by status",
    ["status"],
    registry=REGISTRY,
)

_initialized = False


def prometheus_enabled() -> bool:
    return os.getenv("PROMETHEUS_METRICS_ENABLED", "true").lower() in ("1", "true", "yes")


def prometheus_metrics_token() -> str | None:
    token = os.getenv("PROMETHEUS_METRICS_TOKEN", "").strip()
    return token or None


def _ensure_build_info() -> None:
    global _initialized
    if _initialized:
        return
    BUILD_INFO.info(
        {
            "version": os.getenv("CONTENTOS_VERSION", "0.1.0"),
            "service": "contentos-gateway",
            "environment": os.getenv("APP_ENV", "development"),
        }
    )
    _initialized = True


async def refresh_prometheus_metrics(db: AsyncSession | None = None) -> None:
    """Collect latest values into Prometheus gauges."""
    _ensure_build_info()

    system = collect_system_metrics()
    CPU_PERCENT.set(system.cpu.percent)
    CPU_CORES.set(system.cpu.cores)
    MEMORY_USED_BYTES.set(system.memory.used_mb * 1024 * 1024)
    MEMORY_TOTAL_BYTES.set(system.memory.total_mb * 1024 * 1024)
    MEMORY_PERCENT.set(system.memory.percent)
    DISK_USED_BYTES.set(system.disk.used_gb * 1024**3)
    DISK_TOTAL_BYTES.set(system.disk.total_gb * 1024**3)
    DISK_PERCENT.set(system.disk.percent)

    if system.gpu and system.gpu.available:
        GPU_UTILIZATION.set(system.gpu.utilization)
        GPU_MEMORY_USED_BYTES.set(system.gpu.memory_used_mb * 1024 * 1024)
        GPU_MEMORY_TOTAL_BYTES.set(system.gpu.memory_total_mb * 1024 * 1024)
    else:
        GPU_UTILIZATION.set(0)
        GPU_MEMORY_USED_BYTES.set(0)
        GPU_MEMORY_TOTAL_BYTES.set(0)

    redis_m = await collect_redis_metrics()
    REDIS_UP.set(1 if redis_m.get("status") == "healthy" else 0)
    if redis_m.get("status") == "healthy":
        REDIS_MEMORY_BYTES.set(float(redis_m.get("memory_mb", 0)) * 1024 * 1024)
        REDIS_CONNECTED_CLIENTS.set(float(redis_m.get("connected_clients", 0)))
    else:
        REDIS_MEMORY_BYTES.set(0)
        REDIS_CONNECTED_CLIENTS.set(0)

    if db is not None:
        postgres_m = await collect_postgres_metrics(db)
        POSTGRES_UP.set(1 if postgres_m.get("status") == "healthy" else 0)
        if postgres_m.get("status") == "healthy":
            POSTGRES_LATENCY_SECONDS.set(float(postgres_m.get("latency_ms", 0)) / 1000.0)
            await _refresh_db_counts(db)
        else:
            POSTGRES_LATENCY_SECONDS.set(0)
            _reset_db_counts()
    else:
        POSTGRES_UP.set(0)
        POSTGRES_LATENCY_SECONDS.set(0)
        _reset_db_counts()

    celery_m = await collect_celery_queues()
    CELERY_WORKERS.set(float(celery_m.get("workers", 0)))
    CELERY_PENDING_TOTAL.set(float(celery_m.get("total_pending", 0)))
    queue_depths = celery_m.get("queues", {})
    for queue in AGENT_QUEUES:
        short_name = queue.removeprefix("contentos.")
        CELERY_QUEUE_DEPTH.labels(queue=short_name).set(float(queue_depths.get(queue, 0)))


async def _refresh_db_counts(db: AsyncSession) -> None:
    from contentos_database.models import Job, JobStatus, Pipeline, PipelineStatus

    pipeline_rows = await db.execute(select(Pipeline.status, func.count()).group_by(Pipeline.status))
    pipeline_counts = {status.value: count for status, count in pipeline_rows.all()}
    for status in PipelineStatus:
        PIPELINES_TOTAL.labels(status=status.value).set(float(pipeline_counts.get(status.value, 0)))

    job_rows = await db.execute(select(Job.status, func.count()).group_by(Job.status))
    job_counts = {status.value: count for status, count in job_rows.all()}
    for status in JobStatus:
        JOBS_TOTAL.labels(status=status.value).set(float(job_counts.get(status.value, 0)))


def _reset_db_counts() -> None:
    from contentos_database.models import JobStatus, PipelineStatus

    for status in PipelineStatus:
        PIPELINES_TOTAL.labels(status=status.value).set(0)
    for status in JobStatus:
        JOBS_TOTAL.labels(status=status.value).set(0)


def render_prometheus_metrics() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
