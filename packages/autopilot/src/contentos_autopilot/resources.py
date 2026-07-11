"""Resource readiness contracts for Autopilot.

The resource manager recommends whether and when to execute. It does not control
workers, mutate Celery, start pipelines, or reserve resources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

ReadinessStatus = Literal["ready", "defer", "blocked"]
ExecutionWindow = Literal["now", "soon", "off_peak", "manual_review"]


@dataclass(frozen=True)
class ResourceReadiness:
    status: ReadinessStatus
    score: int
    execution_window: ExecutionWindow
    summary: str
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    gpu_available: bool = False
    gpu_utilization: float | None = None
    queue_pending: int = 0
    workers: int = 0
    blockers: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "score": self.score,
            "execution_window": self.execution_window,
            "summary": self.summary,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "gpu_available": self.gpu_available,
            "gpu_utilization": self.gpu_utilization,
            "queue_pending": self.queue_pending,
            "workers": self.workers,
            "blockers": list(self.blockers),
            "recommendations": list(self.recommendations),
            "guardrails": list(self.guardrails),
            "generated_at": self.generated_at,
        }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _percent(data: Mapping[str, Any] | Any, key: str = "percent") -> float:
    mapping = _as_dict(data)
    try:
        return float(mapping.get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def build_resource_readiness(
    *,
    system_metrics: Mapping[str, Any] | Any,
    celery_metrics: Mapping[str, Any] | Any | None = None,
    requires_gpu: bool = False,
    quantity: int = 1,
) -> ResourceReadiness:
    system = _as_dict(system_metrics)
    celery = _as_dict(celery_metrics or {})
    cpu = _percent(system.get("cpu"))
    memory = _percent(system.get("memory"))
    disk = _percent(system.get("disk"))
    gpu = _as_dict(system.get("gpu"))
    gpu_available = bool(gpu.get("available") or gpu)
    gpu_util = None
    if gpu:
        try:
            gpu_util = float(gpu.get("utilization") or 0.0)
        except (TypeError, ValueError):
            gpu_util = 0.0
    queue_pending = int(celery.get("total_pending") or 0)
    workers = int(celery.get("workers") or 0)
    qty = max(1, int(quantity or 1))

    blockers: list[str] = []
    recommendations: list[str] = []
    penalty = 0

    if cpu >= 92:
        blockers.append("CPU acima de 92%.")
    elif cpu >= 80:
        penalty += 20
        recommendations.append("Aguardar CPU baixar antes de iniciar render pesado.")
    if memory >= 90:
        blockers.append("RAM acima de 90%.")
    elif memory >= 78:
        penalty += 20
        recommendations.append("Reduzir concorrência ou usar modo econômico por RAM elevada.")
    if disk >= 95:
        blockers.append("Disco acima de 95%.")
    elif disk >= 85:
        penalty += 15
        recommendations.append("Limpar renders/assets antigos antes de produção longa.")
    if requires_gpu and not gpu_available:
        blockers.append("GPU requerida, mas não disponível.")
    if gpu_util is not None and gpu_util >= 90:
        penalty += 20
        recommendations.append("GPU ocupada; preferir janela posterior.")
    if workers <= 0:
        blockers.append("Nenhum worker Celery detectado.")
    elif queue_pending > max(workers * 10, qty * 3):
        penalty += 30
        recommendations.append("Fila Celery alta; agendar para janela com menor backlog.")

    score = max(0, min(100, 100 - penalty - len(blockers) * 30))
    if blockers:
        status: ReadinessStatus = "blocked"
        window: ExecutionWindow = "manual_review"
    elif score < 60:
        status = "defer"
        window = "off_peak"
    elif score < 80:
        status = "defer"
        window = "soon"
    else:
        status = "ready"
        window = "now"

    if not recommendations and status == "ready":
        recommendations.append("Recursos saudáveis para iniciar a próxima execução.")

    summary = (
        f"{status}: CPU {cpu:.0f}%, RAM {memory:.0f}%, disco {disk:.0f}%, "
        f"fila {queue_pending}, workers {workers}."
    )
    return ResourceReadiness(
        status=status,
        score=score,
        execution_window=window,
        summary=summary,
        cpu_percent=cpu,
        memory_percent=memory,
        disk_percent=disk,
        gpu_available=gpu_available,
        gpu_utilization=gpu_util,
        queue_pending=queue_pending,
        workers=workers,
        blockers=blockers,
        recommendations=recommendations,
        guardrails=[
            "Resource Manager só recomenda; não controla workers.",
            "Execução continua no Scheduler, Workflow Engine e filas existentes.",
            "Use janela off-peak quando CPU/RAM/fila estiverem altos.",
        ],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )



