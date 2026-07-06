# Grafana Dashboards (Tier E3)

Pre-provisioned dashboards for ContentOS observability stack.

## Quick start

```powershell
docker compose -f docker/docker-compose.yml -f docker/docker-compose.observability.yml up -d
```

Open Grafana: http://localhost:3001 (default `admin` / `admin`)

Folder **ContentOS** contains:

| Dashboard | UID | Content |
|-----------|-----|---------|
| ContentOS — Overview | `contentos-overview` | CPU, RAM, disk, GPU, Postgres, Redis |
| ContentOS — Production | `contentos-production` | Celery queues, pipelines, jobs |

## Datasources (auto-provisioned)

| Name | Type | URL |
|------|------|-----|
| Prometheus | prometheus | http://prometheus:9090 |
| Jaeger | jaeger | http://jaeger:16686 |

Use Jaeger datasource in Grafana Explore for distributed traces (see [OPENTELEMETRY.md](./OPENTELEMETRY.md)).

## File layout

```
docker/grafana/provisioning/
  datasources/datasources.yml
  dashboards/dashboards.yml
  dashboards/json/
    contentos-overview.json
    contentos-production.json
```

Dashboards are editable in the UI; changes persist in the Grafana volume unless you update the JSON manifests in git.

## Requirements

- Gateway running with `PROMETHEUS_METRICS_ENABLED=true`
- Prometheus scraping `gateway:8000/metrics` (configured in `docker/prometheus/prometheus.yml`)
- For traces: `OTEL_ENABLED=true` on gateway, workflow-engine, agents-worker

## Customize

1. Edit JSON under `docker/grafana/provisioning/dashboards/json/`
2. Restart Grafana or wait for the 30s provisioning refresh interval
3. Or duplicate a dashboard in the UI and export JSON back to the repo

## Related

- [PROMETHEUS.md](./PROMETHEUS.md) — metric names and scrape config
- [OPENTELEMETRY.md](./OPENTELEMETRY.md) — tracing setup
- [OBSERVABILITY.md](./OBSERVABILITY.md) — dashboard UI vs Grafana
