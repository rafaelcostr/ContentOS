# RB-003 — Latência alta no PostgreSQL

**Alerta:** `ContentOSPostgresLatencyHigh` · **SLO:** `postgres-latency`

## Sintomas

- `contentos_postgres_latency_seconds > 0.5`
- UI lenta em listagens de pipelines/jobs

## Diagnóstico

```bash
curl -s http://gateway:8000/api/v1/metrics/infrastructure  # JWT
# Grafana → ContentOS Production → Postgres latency
```

## Ações

1. Identificar queries lentas (`pg_stat_statements` se habilitado).
2. Verificar índices em `pipelines`, `jobs`, `log_entries`.
3. Reduzir polling agressivo no dashboard se carga for aceitável.
4. Escalar tier do banco se CPU/IO saturados.

## Thresholds (env)

- Warning: `SLO_POSTGRES_LATENCY_WARNING_MS` (default 300)
- Critical: `SLO_POSTGRES_LATENCY_CRITICAL_MS` (default 500)
