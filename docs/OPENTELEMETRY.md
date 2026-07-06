# OpenTelemetry Tracing (Tier E1)

Distributed tracing across **gateway → workflow-engine → agents-worker** using W3C trace context propagation.

## Quick start

```powershell
docker compose -f docker/docker-compose.yml -f docker/docker-compose.observability.yml up -d --build gateway workflow-engine agents-worker
```

| UI | URL |
|----|-----|
| Jaeger | http://localhost:16686 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

Create a pipeline in the dashboard, then open Jaeger and search service `contentos-gateway` or `contentos-agents-worker`.

## Environment

```env
OTEL_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_EXPORTER_OTLP_INSECURE=true
OTEL_FASTAPI_EXCLUDED_URLS=/health,/metrics
CONTENTOS_VERSION=0.1.0
```

Tracing is **off by default** (`OTEL_ENABLED=false`). Enable when running with Jaeger or any OTLP-compatible collector.

## Architecture

```
Dashboard / API client
    ↓ HTTP (auto-instrumented FastAPI)
contentos-gateway
    ↓ httpx → workflow-engine (traceparent header)
contentos-workflow-engine
    ↓ Celery (_trace_carrier in task kwargs)
contentos-agents-worker
    ↓ agent.{step}.execute span
    ↓ httpx callback → workflow-engine
```

### Instrumentation

| Component | Mechanism |
|-----------|-----------|
| Gateway | `FastAPIInstrumentor` + `HTTPXClientInstrumentor` |
| Workflow engine | Same FastAPI + httpx instrumentation |
| Agents worker | Manual span `agent.{step}.execute` + carrier from Celery |
| Celery dispatch | W3C context injected in `_trace_carrier` task kwarg |

Module: `packages/shared/src/contentos_shared/telemetry.py`

## Span attributes (agents)

- `contentos.step`
- `contentos.job_id`
- `contentos.pipeline_id`
- `contentos.project_id`

## Production notes

- Point `OTEL_EXPORTER_OTLP_ENDPOINT` to your collector (Grafana Tempo, Datadog agent, etc.).
- Set `OTEL_EXPORTER_OTLP_INSECURE=false` when using TLS.
- Combine with [OPENTELEMETRY.md](./OPENTELEMETRY.md) for trace correlation in Grafana/Jaeger.

## Related

- JSON metrics (dashboard UI): `/api/v1/metrics/*`
- Prometheus scrape: `/metrics`
