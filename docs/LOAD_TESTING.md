# Load testing & gateway hardening — V5.5.4

Testes de carga smoke + hardening do API gateway para produção.

## Hardening do gateway

| Controle | Env | Default |
|----------|-----|---------|
| Rate limit global | `GATEWAY_RATE_LIMIT_ENABLED` | `true` |
| Requisições/min por IP | `GATEWAY_RATE_LIMIT_PER_MINUTE` | `300` |
| Timeout por request | `GATEWAY_REQUEST_TIMEOUT_SECONDS` | `120` |
| Paths isentos | `GATEWAY_RATE_LIMIT_EXEMPT_PATHS` | `/health,/health/ready,/metrics,...` |

Respostas:
- **429** — rate limit (`Retry-After: 60`)
- **504** — timeout do handler

### Readiness (K8s)

| Path | Uso |
|------|-----|
| `GET /health` | Liveness — processo vivo |
| `GET /health/ready` | Readiness — Postgres + Redis OK |

Production overlay usa `/health/ready` no `readinessProbe` (`patch-gateway-hardening.yaml`).

## Smoke load test

### Opção A — k6 (recomendado)

```bash
# Instalar k6: https://k6.io/docs/get-started/installation/
docker compose -f docker/docker-compose.yml up -d gateway

BASE_URL=http://localhost:8000 k6 run scripts/loadtest/k6-smoke.js

# Com JWT (opcional) para exercitar /api/v1/projects
AUTH_TOKEN=eyJ... BASE_URL=http://localhost:8000 k6 run scripts/loadtest/k6-smoke.js
```

Thresholds k6:
- `http_req_failed < 2%`
- `p(95) < 800ms`

### Opção B — Python (sem k6)

```powershell
python scripts/loadtest/smoke_load.py --base-url http://localhost:8000 --concurrency 20 --duration 30
```

### Wrapper

```powershell
.\scripts\loadtest\run_loadtest.ps1 -BaseUrl http://localhost:8000
```

Usa k6 se instalado; caso contrário, fallback Python.

## CI / pré-deploy

1. Stack local up (`gateway` + `postgres` + `redis`)
2. `pytest tests/test_gateway_hardening.py -q`
3. `python scripts/loadtest/smoke_load.py` (ou k6 em pipeline com service container)

## Kubernetes

```bash
kubectl apply -k k8s/overlays/production/
kubectl -n contentos get deployment gateway -o yaml | grep -A2 readinessProbe
```

## Arquivos

| Path | Descrição |
|------|-----------|
| `middleware/hardening.py` | Rate limit + timeout |
| `services/gateway_rate_limiter.py` | Redis/in-memory limiter |
| `scripts/loadtest/k6-smoke.js` | Cenário k6 |
| `scripts/loadtest/smoke_load.py` | Smoke async Python |
| `k8s/overlays/production/patch-gateway-hardening.yaml` | Probes + resources |

## Relacionados

- [PRODUCTION_HARDENING.md](./PRODUCTION_HARDENING.md)
- [SLO_ALERTS_RUNBOOKS.md](./SLO_ALERTS_RUNBOOKS.md)
