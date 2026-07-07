# Prometheus / Grafana (Tier E2)

ContentOS exposes a standard **Prometheus scrape endpoint** at `GET /metrics` on the API gateway.

## Quick start

```powershell
# Stack + observability
docker compose -f docker/docker-compose.yml -f docker/docker-compose.observability.yml up -d --build gateway

# Scrape locally
curl http://localhost:8000/metrics
```

| Service | URL | Default credentials |
|---------|-----|---------------------|
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3001 | admin / admin |

Grafana ships with Prometheus + Jaeger datasources and pre-built dashboards in folder **ContentOS** — see [GRAFANA.md](./GRAFANA.md).

Alert rules (V5.5.3): `docker/prometheus/alerts/contentos.yml` — see [SLO_ALERTS_RUNBOOKS.md](./SLO_ALERTS_RUNBOOKS.md).

## Environment

```env
PROMETHEUS_METRICS_ENABLED=true
# Optional — when set, scrapers must send Bearer token or X-Prometheus-Token
PROMETHEUS_METRICS_TOKEN=

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
CONTENTOS_VERSION=0.1.0
```

## Exported metrics

| Metric | Type | Description |
|--------|------|-------------|
| `contentos_build_info` | info | version, service, environment |
| `contentos_cpu_percent` | gauge | CPU utilization |
| `contentos_cpu_cores` | gauge | CPU core count |
| `contentos_memory_*` | gauge | RAM used/total/percent |
| `contentos_disk_*` | gauge | Disk used/total/percent |
| `contentos_gpu_*` | gauge | GPU util + VRAM (0 when unavailable) |
| `contentos_redis_up` | gauge | Redis health |
| `contentos_redis_memory_bytes` | gauge | Redis memory |
| `contentos_redis_connected_clients` | gauge | Redis clients |
| `contentos_postgres_up` | gauge | PostgreSQL health |
| `contentos_postgres_latency_seconds` | gauge | DB round-trip latency |
| `contentos_celery_workers` | gauge | Active Celery workers |
| `contentos_celery_pending_total` | gauge | Total queued tasks |
| `contentos_celery_queue_depth{queue}` | gauge | Depth per agent queue |
| `contentos_pipelines_total{status}` | gauge | Pipelines by status |
| `contentos_jobs_total{status}` | gauge | Jobs by status |

Values refresh on each scrape (pull model). System/infra collectors reuse the same TTL cache as `/api/v1/metrics/*`.

## Kubernetes / production

- Scrape `http://contentos-gateway:8000/metrics` every 15–30s.
- Set `PROMETHEUS_METRICS_TOKEN` and configure the Prometheus `authorization` credentials block.
- Disable with `PROMETHEUS_METRICS_ENABLED=false` if an sidecar exporter is used instead.

## Related

- JSON metrics for the dashboard UI remain at `/api/v1/metrics/system` and `/api/v1/metrics/infrastructure` (JWT required).
- See also [OBSERVABILITY.md](./OBSERVABILITY.md).
