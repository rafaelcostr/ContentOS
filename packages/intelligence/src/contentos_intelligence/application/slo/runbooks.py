"""Runbook catalog — V5.5.3."""

from __future__ import annotations

from typing import Any

RUNBOOKS: tuple[dict[str, Any], ...] = (
    {
        "id": "redis-down",
        "title": "Redis indisponível",
        "severity": "critical",
        "doc_path": "docs/runbooks/RB-001-redis-down.md",
        "summary": "Restaurar broker Celery / cache Redis",
    },
    {
        "id": "postgres-down",
        "title": "PostgreSQL indisponível",
        "severity": "critical",
        "doc_path": "docs/runbooks/RB-002-postgres-down.md",
        "summary": "Recuperar conectividade com o banco primário",
    },
    {
        "id": "postgres-latency",
        "title": "Latência alta no PostgreSQL",
        "severity": "warning",
        "doc_path": "docs/runbooks/RB-003-postgres-latency.md",
        "summary": "Investigar queries lentas e carga no banco",
    },
    {
        "id": "celery-workers-zero",
        "title": "Sem workers Celery",
        "severity": "critical",
        "doc_path": "docs/runbooks/RB-004-celery-workers-zero.md",
        "summary": "Restaurar pools de workers (KEDA / deployments)",
    },
    {
        "id": "queue-backlog",
        "title": "Backlog de filas Celery",
        "severity": "warning",
        "doc_path": "docs/runbooks/RB-005-queue-backlog.md",
        "summary": "Escalar workers ou reduzir carga de entrada",
    },
    {
        "id": "pipeline-failures",
        "title": "Falhas de pipeline",
        "severity": "critical",
        "doc_path": "docs/runbooks/RB-006-pipeline-failures.md",
        "summary": "Triagem de pipelines failed e retry policy",
    },
    {
        "id": "job-failures",
        "title": "Falhas de jobs de agente",
        "severity": "warning",
        "doc_path": "docs/runbooks/RB-007-job-failures.md",
        "summary": "Analisar steps com alta taxa de falha",
    },
)


def list_runbooks() -> list[dict[str, Any]]:
    return [dict(r) for r in RUNBOOKS]


def get_runbook(runbook_id: str) -> dict[str, Any] | None:
    for rb in RUNBOOKS:
        if rb["id"] == runbook_id:
            return dict(rb)
    return None
