# SLO, alertas e runbooks — V5.5.3

Observabilidade operacional enterprise: **SLOs avaliados em tempo real**, **alertas Prometheus** e **runbooks** linkados.

## SLOs definidos

| ID | Nome | Target default | Runbook |
|----|------|----------------|---------|
| `redis-availability` | Redis | healthy | [RB-001](./runbooks/RB-001-redis-down.md) |
| `postgres-availability` | PostgreSQL | healthy | [RB-002](./runbooks/RB-002-postgres-down.md) |
| `postgres-latency` | Latência DB | < 500ms | [RB-003](./runbooks/RB-003-postgres-latency.md) |
| `celery-workers` | Workers Celery | >= 1 | [RB-004](./runbooks/RB-004-celery-workers-zero.md) |
| `queue-backlog` | Backlog total | <= 50 (warn) | [RB-005](./runbooks/RB-005-queue-backlog.md) |
| `pipeline-success-24h` | Pipelines 24h | >= 95% | [RB-006](./runbooks/RB-006-pipeline-failures.md) |
| `job-success-24h` | Jobs 24h | >= 90% | [RB-007](./runbooks/RB-007-job-failures.md) |

Estados: `ok` · `warning` · `critical` · `unknown`

## API

| Method | Path | Descrição |
|--------|------|-----------|
| `GET` | `/api/v1/ops/slo` | Relatório SLO da plataforma |
| `GET` | `/api/v1/ops/runbooks` | Catálogo de runbooks |
| `GET` | `/api/v1/ops/runbooks/{id}` | Metadados de um runbook |

O **Command Center** (`/executive`) inclui `slo_items[]` e mescla alertas SLO em `alerts[]`.

## Variáveis de ambiente

```env
SLO_POSTGRES_LATENCY_WARNING_MS=300
SLO_POSTGRES_LATENCY_CRITICAL_MS=500
SLO_QUEUE_BACKLOG_WARNING=50
SLO_QUEUE_BACKLOG_CRITICAL=150
SLO_PIPELINE_SUCCESS_MIN_PERCENT=95
SLO_JOB_SUCCESS_MIN_PERCENT=90
SLO_MIN_CELERY_WORKERS=1
```

## Alertas Prometheus

Regras em `docker/prometheus/alerts/contentos.yml`, carregadas pelo stack observability.

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.observability.yml up -d
open http://localhost:9090/alerts
```

| Alerta | Severidade | Runbook ID |
|--------|------------|------------|
| ContentOSRedisDown | critical | redis-down |
| ContentOSPostgresDown | critical | postgres-down |
| ContentOSPostgresLatencyHigh | warning | postgres-latency |
| ContentOSCeleryWorkersZero | critical | celery-workers-zero |
| ContentOSQueueBacklogHigh | critical | queue-backlog |
| ContentOSQueueBacklogWarning | warning | queue-backlog |
| ContentOSPipelineFailures | warning | pipeline-failures |
| ContentOSJobFailures | warning | job-failures |

## Componentes

| Módulo | Path |
|--------|------|
| Domínio SLO | `packages/intelligence/.../domain/slo.py` |
| Avaliador | `application/slo/evaluator.py` |
| Gateway snapshot | `services/slo_service.py` |
| API ops | `api/routes/ops.py` |

## Testes

```powershell
pytest tests/test_slo.py tests/test_executive_dashboard.py -q
```

## Relacionados

- [COMMAND_CENTER.md](./COMMAND_CENTER.md)
- [PROMETHEUS.md](./PROMETHEUS.md)
- [KEDA_PRODUCTION.md](./KEDA_PRODUCTION.md)
