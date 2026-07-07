# RB-006 — Falhas de pipeline

**Alerta:** `ContentOSPipelineFailures` · **SLO:** `pipeline-success-24h`

## Sintomas

- Pipelines em status `failed` no dashboard `/jobs`
- SLO de sucesso 24h abaixo de 95%

## Diagnóstico

1. Command Center → alertas `[SLO] Pipeline success`
2. `GET /api/v1/pipelines` — filtrar `status=failed`
3. Inspecionar `error_message` e último step no detalhe do pipeline

## Ações

1. Corrigir causa raiz do step (provider down, quota, asset missing).
2. Reexecutar pipeline ou usar `auto_retry` se política aplicável.
3. Para falhas em massa: verificar Ollama, MinIO, FFmpeg.
4. Documentar incidente se taxa < 90% por > 1h.

## Threshold

`SLO_PIPELINE_SUCCESS_MIN_PERCENT` (default 95)
