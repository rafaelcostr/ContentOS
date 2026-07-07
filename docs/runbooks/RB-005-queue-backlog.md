# RB-005 — Backlog de filas Celery

**Alerta:** `ContentOSQueueBacklogHigh` / `ContentOSQueueBacklogWarning` · **SLO:** `queue-backlog`

## Sintomas

- `contentos_celery_pending_total` elevado
- Tempo de pipeline muito acima do normal

## Diagnóstico

```bash
curl -s http://gateway:8000/metrics | grep contentos_celery_queue_depth
# ou /api/v1/agents (JWT) — depth por fila
```

## Ações

1. Identificar fila com maior depth (editor, media_analyze, publisher, etc.).
2. Escalar pool correspondente via KEDA ou scale manual.
3. Pausar lotes na Content Factory se backlog for intencional (`/factory`).
4. Verificar workers com OOM/restart loop.

## Thresholds (env)

- Warning: `SLO_QUEUE_BACKLOG_WARNING` (default 50)
- Critical: `SLO_QUEUE_BACKLOG_CRITICAL` (default 150)
