# RB-007 — Falhas de jobs de agente

**Alerta:** `ContentOSJobFailures` · **SLO:** `job-success-24h`

## Sintomas

- Jobs `failed` em steps específicos
- SLO job success 24h abaixo de 90%

## Diagnóstico

```bash
# Dashboard /agents — step com maior fail rate
GET /api/v1/agents/{step}
GET /api/v1/logs?job_id=...
```

## Ações

1. Agrupar falhas por `step` (editor, voice, media_analyze, etc.).
2. Verificar provider do step em `/analytics/providers`.
3. Ajustar retries (`max_retries`) ou DNA/workflow se erro sistemático.
4. Escalar pool do step se timeout por fila.

## Threshold

`SLO_JOB_SUCCESS_MIN_PERCENT` (default 90)
