"""System and infrastructure metrics — observability layer."""

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")

_cache: dict[str, tuple[float, Any]] = {}


def _cached(key: str, ttl_seconds: float, factory: Callable[[], T]) -> T:
    now = time.monotonic()
    entry = _cache.get(key)
    if entry and now - entry[0] < ttl_seconds:
        return entry[1]
    value = factory()
    _cache[key] = (now, value)
    return value


async def _cached_async(key: str, ttl_seconds: float, factory: Callable[[], Awaitable[T]]) -> T:
    now = time.monotonic()
    entry = _cache.get(key)
    if entry and now - entry[0] < ttl_seconds:
        return entry[1]
    value = await factory()
    _cache[key] = (now, value)
    return value


@dataclass
class CpuMetrics:
    percent: float
    cores: int


@dataclass
class MemoryMetrics:
    used_mb: float
    total_mb: float
    percent: float


@dataclass
class DiskMetrics:
    used_gb: float
    total_gb: float
    percent: float


@dataclass
class GpuMetrics:
    available: bool
    name: str = ""
    utilization: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0


@dataclass
class SystemMetrics:
    cpu: CpuMetrics
    memory: MemoryMetrics
    disk: DiskMetrics
    gpu: GpuMetrics | None = None


AGENT_QUEUES = [
    "contentos.trend_intelligence",
    "contentos.research",
    "contentos.hook",
    "contentos.script",
    "contentos.script_review",
    "contentos.emotion",
    "contentos.content_score",
    "contentos.content_intelligence",
    "contentos.scene",
    "contentos.storyboard",
    "contentos.scene_director",
    "contentos.clip_research",
    "contentos.asset_collector",
    "contentos.asset_index",
    "contentos.media_analyze",
    "contentos.asset_search",
    "contentos.takes",
    "contentos.voice",
    "contentos.subtitle",
    "contentos.editor",
    "contentos.quality",
    "contentos.video_review",
    "contentos.auto_retry",
    "contentos.publisher",
    "contentos.seo",
    "contentos.ai_director",
    "contentos.creative_memory",
    "contentos.multi_content",
    "contentos.multi_content_video",
    "contentos.learning",
    "contentos.knowledge_base",
]

AGENT_PROVIDER_MAP: dict[str, dict[str, str]] = {
    "trend_intelligence": {"provider": "rules", "model_env": "", "default_model": "memory+analytics"},
    "research": {"provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "hook": {"provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "script": {"provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "script_review": {"provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "emotion": {"provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "content_score": {"provider": "rules", "model_env": "", "default_model": "score-aggregator"},
    "content_intelligence": {"provider": "rules", "model_env": "", "default_model": "viral+reuse"},
    "video_review": {"provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "auto_retry": {"provider": "rules", "model_env": "", "default_model": "creative-retry-policy"},
    "storyboard": {"provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "scene_director": {"provider": "rules", "model_env": "", "default_model": "storyboard-mapper"},
    "scene": {"provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "clip_research": {"provider": "content-sources", "model_env": "", "default_model": "source-manager"},
    "asset_collector": {"provider": "content-sources", "model_env": "", "default_model": "asset-pipeline"},
    "asset_index": {"provider": "postgres", "model_env": "", "default_model": "asset-index"},
    "media_analyze": {"provider": "ollama", "model_env": "MEDIA_VISION_MODEL", "default_model": "llava"},
    "asset_search": {"provider": "postgres", "model_env": "", "default_model": "asset-search"},
    "publisher": {"provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "seo": {"provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "ai_director": {"provider": "rules", "model_env": "", "default_model": "director-planner"},
    "creative_memory": {"provider": "rules", "model_env": "", "default_model": "memory+kb"},
    "multi_content": {"provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "multi_content_video": {"provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "learning": {"provider": "rules", "model_env": "", "default_model": "memory+kb"},
    "knowledge_base": {"provider": "postgres", "model_env": "", "default_model": "kb-indexer"},
    "voice": {"provider": "piper", "model_env": "PIPER_VOICE", "default_model": "pt_BR-faber-medium"},
    "subtitle": {"provider": "whisper", "model_env": "WHISPER_MODEL", "default_model": "large-v3"},
    "editor": {"provider": "ffmpeg", "model_env": "", "default_model": "libx264 1080x1920@60"},
    "takes": {"provider": "minio", "model_env": "", "default_model": "take-library"},
    "quality": {"provider": "ffprobe", "model_env": "", "default_model": "validation"},
}


def collect_cpu() -> CpuMetrics:
    try:
        import psutil

        return CpuMetrics(percent=psutil.cpu_percent(interval=None), cores=psutil.cpu_count() or 1)
    except ImportError:
        return CpuMetrics(percent=0.0, cores=1)


def collect_memory() -> MemoryMetrics:
    try:
        import psutil

        mem = psutil.virtual_memory()
        return MemoryMetrics(
            used_mb=round(mem.used / (1024 * 1024), 1),
            total_mb=round(mem.total / (1024 * 1024), 1),
            percent=mem.percent,
        )
    except ImportError:
        return MemoryMetrics(used_mb=0, total_mb=0, percent=0)


def collect_disk(path: str = "/") -> DiskMetrics:
    try:
        usage = shutil.disk_usage(path)
        total_gb = usage.total / (1024**3)
        used_gb = usage.used / (1024**3)
        return DiskMetrics(
            used_gb=round(used_gb, 1),
            total_gb=round(total_gb, 1),
            percent=round(usage.used / usage.total * 100, 1) if usage.total else 0,
        )
    except OSError:
        usage = shutil.disk_usage(".")
        return DiskMetrics(
            used_gb=round(usage.used / (1024**3), 1),
            total_gb=round(usage.total / (1024**3), 1),
            percent=round(usage.used / usage.total * 100, 1),
        )


def collect_gpu() -> GpuMetrics | None:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return GpuMetrics(available=False)
        line = result.stdout.strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            return GpuMetrics(available=False)
        return GpuMetrics(
            available=True,
            name=parts[0],
            utilization=float(parts[1]),
            memory_used_mb=float(parts[2]),
            memory_total_mb=float(parts[3]),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return GpuMetrics(available=False)


def collect_system_metrics() -> SystemMetrics:
    def _collect() -> SystemMetrics:
        gpu = collect_gpu()
        return SystemMetrics(
            cpu=collect_cpu(),
            memory=collect_memory(),
            disk=collect_disk(),
            gpu=gpu if gpu and gpu.available else None,
        )

    return _cached("system_metrics", 5.0, _collect)


async def collect_redis_metrics(redis_url: str | None = None) -> dict:
    url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(url)
        info = await client.info("memory")
        clients = await client.info("clients")
        await client.ping()
        await client.aclose()
        return {
            "status": "healthy",
            "memory_mb": round(int(info.get("used_memory", 0)) / (1024 * 1024), 1),
            "connected_clients": int(clients.get("connected_clients", 0)),
        }
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


async def collect_postgres_metrics(db) -> dict:
    import time

    from sqlalchemy import text

    try:
        start = time.perf_counter()
        await db.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - start) * 1000, 1)
        return {"status": "healthy", "latency_ms": latency}
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


async def _collect_celery_queues_raw(redis_url: str | None = None) -> dict:
    url = redis_url or os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    queues: dict[str, int] = {}
    workers = 0
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(url)
        for q in AGENT_QUEUES:
            depth = await client.llen(q)
            queues[q] = depth
        await client.aclose()
    except Exception:
        queues = {q: 0 for q in AGENT_QUEUES}

    try:
        from celery import Celery

        app = Celery(broker=url)
        inspect = app.control.inspect(timeout=0.5)
        stats = inspect.stats()
        workers = len(stats) if stats else 0
    except Exception:
        workers = 0

    return {"workers": workers, "queues": queues, "total_pending": sum(queues.values())}


async def collect_celery_queues(redis_url: str | None = None) -> dict:
    cache_key = f"celery_queues:{redis_url or 'default'}"
    return await _cached_async(cache_key, 10.0, lambda: _collect_celery_queues_raw(redis_url))


def agent_model(step: str) -> tuple[str, str]:
    try:
        from contentos_models import get_model_manager

        return get_model_manager().provider_and_model(step)
    except ImportError:
        pass
    meta = AGENT_PROVIDER_MAP.get(step, {"provider": "unknown", "model_env": "", "default_model": "—"})
    model_env = meta.get("model_env", "")
    model = os.getenv(model_env, meta.get("default_model", "—")) if model_env else meta.get("default_model", "—")
    return meta.get("provider", "unknown"), model


PROVIDER_USAGE_STEPS: dict[str, list[str]] = {
    "ollama": [
        "research",
        "hook",
        "script",
        "script_review",
        "emotion",
        "video_review",
        "storyboard",
        "scene",
        "publisher",
        "seo",
        "multi_content",
        "multi_content_video",
        "analytics",
        "thumbnail",
        "clip_research",
    ],
    "rules": [
        "trend_intelligence",
        "content_score",
        "content_intelligence",
        "auto_retry",
        "scene_director",
        "ai_director",
        "creative_memory",
        "learning",
    ],
    "postgres": ["asset_index", "media_analyze", "asset_search", "knowledge_base"],
    "content-sources": ["asset_collector"],
    "piper": ["voice"],
    "whisper": ["subtitle"],
    "ffmpeg": ["editor"],
    "ffprobe": ["quality"],
    "minio": ["takes"],
}

