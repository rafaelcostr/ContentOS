# ContentOS — Observabilidade (Fase 4)

## Dashboard de produção

### Métricas de sistema

`GET /api/v1/metrics/system`

| Métrica | Fonte |
|---------|-------|
| CPU % | psutil |
| RAM % / MB | psutil |
| Disco % / GB | shutil.disk_usage |
| GPU / VRAM | nvidia-smi (se disponível) |

### Infraestrutura

`GET /api/v1/metrics/infrastructure`

| Serviço | Métricas |
|---------|----------|
| PostgreSQL | status, latency_ms |
| Redis | status, memory_mb, connected_clients |
| Celery | workers ativos, depth por fila |

---

## Agentes

`GET /api/v1/agents` — stats em tempo real:

- Status: `online` | `running` | `idle` | `queued`
- Provider + modelo (Ollama, Piper, Whisper, FFmpeg)
- Fila Celery (depth)
- Execuções ok/fail, tempo médio
- Última execução
- 5 logs recentes

`GET /api/v1/agents/{name}` — detalhe individual

---

## Analytics por Provider

`GET /api/v1/analytics/providers`

Agrupa jobs por provider:

| Provider | Steps |
|----------|-------|
| ollama | research, script, scene, publisher |
| piper | voice |
| whisper | subtitle |
| ffmpeg | editor |
| ffprobe | quality |
| minio | takes |

Inclui taxa de sucesso + health check dos serviços externos.

---

## Dashboard UI

| Página | Conteúdo |
|--------|----------|
| `/` | CPU/RAM/GPU, infra, agentes, WebSocket |
| `/agents` | Cards + painel de detalhe com logs |
| `/analytics` | Providers, recursos, performance por step |
| `/jobs` | Pipeline tempo real (Fase 3) |

Polling automático: 8–20s conforme página.

### Prometheus (Tier E2)

`GET /metrics` — formato Prometheus text (sem JWT; token opcional via `PROMETHEUS_METRICS_TOKEN`).

Stack opcional: `docker compose -f docker/docker-compose.yml -f docker/docker-compose.observability.yml up -d`

Ver [PROMETHEUS.md](./PROMETHEUS.md).

### OpenTelemetry (Tier E1)

Distributed tracing gateway → workflow-engine → agents. See [OPENTELEMETRY.md](./OPENTELEMETRY.md).

Jaeger UI: http://localhost:16686 (with observability compose overlay).

Grafana dashboards provisionados: pasta **ContentOS** em http://localhost:3001 — ver [GRAFANA.md](./GRAFANA.md).

---

## Arquitetura

```
Dashboard (React Query polling)
    ↓
API Gateway
    ├── metrics_collector.py (psutil, redis, celery inspect, nvidia-smi)
    ├── agents.py (Job stats + LogEntry + queue depth)
    └── analytics/providers (aggregate by PROVIDER_USAGE_STEPS)
```

---

## GPU no Docker

Para expor GPU ao gateway (métricas):

```yaml
# docker-compose.gpu.yml — adicionar ao gateway se necessário
```

Métricas GPU retornam `null` quando `nvidia-smi` não está disponível — comportamento esperado em CPU-only.
