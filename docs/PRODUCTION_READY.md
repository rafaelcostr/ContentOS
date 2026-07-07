# ContentOS — Production Ready (V5.5.5)

Checklist **final de go-live** consolidando V5.5 Enterprise + hardening V4. Use como gate antes de abrir tráfego real.

| Campo | Valor |
|-------|--------|
| **Versão alvo** | ContentOS V5 |
| **Última fase** | V5.5.5 |
| **Base técnica** | [V5_ROADMAP.md](./V5_ROADMAP.md) · [PRODUCTION_HARDENING.md](./PRODUCTION_HARDENING.md) |

---

## Critério de “Production Ready”

Todos os blocos **obrigatórios** abaixo devem estar marcados. Itens **recomendados** podem ser adiados com risco documentado.

| Bloco | Obrigatório |
|-------|-------------|
| Infra & secrets | Sim |
| Kubernetes & workers | Sim |
| Gateway hardening | Sim |
| Observabilidade & SLO | Sim |
| Qualidade de conteúdo | Sim |
| Smoke / load test | Sim |
| V5 funcional (smoke) | Sim |
| Segurança & multi-tenant | Sim |
| CI/CD & rollback | Recomendado |

---

## 1. Infraestrutura & secrets

- [ ] PostgreSQL managed (RDS / Cloud SQL) com backups automáticos
- [ ] Redis managed (ElastiCache / Memorystore) para Celery + cache
- [ ] Object storage S3-compatible (MinIO ou cloud) com bucket dedicado
- [ ] `JWT_SECRET` rotacionado (64+ caracteres hex)
- [ ] Secrets reais em K8s (`contentos-secrets`) ou External Secrets Operator
- [ ] `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL` validados nos pods
- [ ] Ollama / AI Gateway / Piper / Whisper acessíveis apenas na rede interna

```bash
kubectl -n contentos get secret contentos-secrets
kubectl -n contentos exec deployment/gateway -- env | grep -E 'DATABASE|REDIS|JWT'
```

---

## 2. Kubernetes & workers (V5.5.2)

- [ ] Overlay production aplicado: `kubectl apply -k k8s/overlays/production/`
- [ ] KEDA instalado no cluster
- [ ] Pools ativos: `research`, `script`, `editor`, `general`, `v5-quality`, `v5-media`
- [ ] ScaledObjects sem erro: `kubectl -n contentos get scaledobject`
- [ ] Ingress + TLS (cert-manager) com domínio real
- [ ] `workflow-engine` e `ai-gateway` **não** expostos publicamente

Ver [K8S.md](./K8S.md) · [KEDA_PRODUCTION.md](./KEDA_PRODUCTION.md)

```bash
kubectl -n contentos get pods -l app=agents-worker
kubectl -n contentos describe scaledobject agents-worker-v5-quality-scaler
```

---

## 3. Gateway hardening (V5.5.4)

- [ ] `GATEWAY_RATE_LIMIT_ENABLED=true`
- [ ] `GATEWAY_RATE_LIMIT_PER_MINUTE` definido (default 300)
- [ ] `GATEWAY_REQUEST_TIMEOUT_SECONDS=120`
- [ ] Liveness: `GET /health`
- [ ] Readiness: `GET /health/ready` (Postgres + Redis)
- [ ] `CORS_ORIGINS` apontando para URL do dashboard em produção
- [ ] `PROMETHEUS_METRICS_TOKEN` se `/metrics` estiver no ingress público

Ver [LOAD_TESTING.md](./LOAD_TESTING.md)

```bash
curl -s https://api.seudominio.com/health
curl -s https://api.seudominio.com/health/ready
```

---

## 4. Observabilidade & SLO (V5.5.3)

- [ ] Prometheus scrape `GET /metrics` a cada 15–30s
- [ ] Regras de alerta carregadas (`docker/prometheus/alerts/contentos.yml` ou equivalente)
- [ ] Grafana pasta **ContentOS** provisionada
- [ ] OpenTelemetry → Jaeger/Tempo (`OTEL_ENABLED=true`)
- [ ] `GET /api/v1/ops/slo` retorna todos os SLOs `ok` ou `warning` aceito
- [ ] Runbooks revisados pela equipe on-call

Ver [PROMETHEUS.md](./PROMETHEUS.md) · [SLO_ALERTS_RUNBOOKS.md](./SLO_ALERTS_RUNBOOKS.md) · [GRAFANA.md](./GRAFANA.md)

```bash
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].name'
# JWT
curl -s -H "Authorization: Bearer $TOKEN" https://api.seudominio.com/api/v1/ops/slo
```

---

## 5. Command Center (V5.5.1)

- [ ] Dashboard `/executive` acessível com KPIs V4 + V5
- [ ] Alertas operacionais (factory, community, OAuth) funcionando
- [ ] `slo_items[]` visíveis no Command Center
- [ ] Polling estável (60s) sem erros 5xx

Ver [COMMAND_CENTER.md](./COMMAND_CENTER.md)

---

## 6. Qualidade de conteúdo

- [ ] `QUALITY_MIN_SCORE=6` (técnico)
- [ ] `VIDEO_REVIEW_MIN_SCORE=8` (criativo)
- [ ] `APP_ENV=production` com `RENDER_ALLOW_PLACEHOLDER=false` (padrão em prod)
- [ ] `MEDIA_REQUIRE_ASSETS=true` e `MEDIA_REQUIRE_CLIPS=true` em produção
- [ ] `PUBLISH_REQUIRE_QA=true` em produção (bloqueia `live` se QA falhar)
- [ ] `PUBLISH_MODE` configurado (`dry_run` → `prepare_only` → `live`)
- [ ] Content Factory: aprovação humana antes de publicar lote (`factory_pending_approval`)
- [ ] Community Agent: **apenas rascunhos** (sem auto-post)

Ver [QUALITY.md](./QUALITY.md) · [CONTENT_FACTORY.md](./CONTENT_FACTORY.md) · [COMMUNITY_AGENT.md](./COMMUNITY_AGENT.md)

---

## 7. Smoke funcional V5

Executar em **staging** antes de produção:

| Área | Comando / ação | Esperado |
|------|----------------|----------|
| Mídia V5.0 | `pytest tests/test_v5_media_autopilot.py -q` | pass |
| Voice / DNA | `pytest tests/test_voice_studio.py tests/test_dna_v2.py -q` | pass |
| Retention / SEO | `pytest tests/test_retention_engine.py tests/test_seo_engine.py -q` | pass |
| Content Factory | `pytest tests/test_content_factory.py -q` | pass |
| OAuth analytics | `pytest tests/test_platform_analytics.py -q` | pass |
| Performance learning | `pytest tests/test_performance_learning.py tests/test_media_production.py -q` | pass |
| Pipeline E2E | `python scripts/e2e_pipeline.py` (stack up) | MP4 gerado |

```powershell
# Suite V5 resumida
pytest tests/test_v5_media_autopilot.py tests/test_content_factory.py tests/test_slo.py tests/test_gateway_hardening.py tests/test_k8s_manifests.py -q
```

---

## 8. Load test (V5.5.4)

- [ ] Smoke load executado contra staging/production-like
- [ ] `http_req_failed < 2%` (k6) ou `error_rate < 5%` (Python)
- [ ] `p95 < 800ms` em `/health` sob carga configurada
- [ ] Sem OOM/restart em `gateway` durante o teste

```powershell
.\scripts\loadtest\run_loadtest.ps1 -BaseUrl https://api.staging.seudominio.com
# ou
BASE_URL=https://api.staging.seudominio.com k6 run scripts/loadtest/k6-smoke.js
```

---

## 9. Segurança & multi-tenant

- [ ] RBAC revisado — [RBAC.md](./RBAC.md)
- [ ] API keys por organização com rate limit — [API_KEYS.md](./API_KEYS.md)
- [ ] Billing / quotas habilitados se SaaS — [BILLING.md](./BILLING.md) · [QUOTAS.md](./QUOTAS.md)
- [ ] OAuth scopes mínimos (analytics + comments conforme uso)
- [ ] Logs sem PII/tokens em plain text

---

## 10. CI/CD & rollback

- [ ] Staging deploy automático validado — [DEPLOY_STAGING.md](./DEPLOY_STAGING.md)
- [ ] Imagens production taggeadas (`ghcr.io/contentos/*:production`)
- [ ] Plano de rollback documentado (`kubectl rollout undo deployment/gateway`)
- [ ] Backup DB testado (restore em staging)

---

## Verificação automatizada (local)

```powershell
# Manifests K8s + docs V5
pytest tests/test_production_ready.py tests/test_k8s_manifests.py -q

# Kustomize production build
kubectl kustomize k8s/overlays/production/ | findstr /i "health/ready GATEWAY_RATE_LIMIT"
```

---

## Sign-off

| Papel | Nome | Data | OK |
|-------|------|------|-----|
| Engenharia | | | [ ] |
| Operações / SRE | | | [ ] |
| Produto | | | [ ] |

---

## Mapa de documentação V5.5

| Doc | Conteúdo |
|-----|----------|
| [COMMAND_CENTER.md](./COMMAND_CENTER.md) | V5.5.1 — `/executive` |
| [KEDA_PRODUCTION.md](./KEDA_PRODUCTION.md) | V5.5.2 — workers |
| [SLO_ALERTS_RUNBOOKS.md](./SLO_ALERTS_RUNBOOKS.md) | V5.5.3 — SLO + alertas |
| [LOAD_TESTING.md](./LOAD_TESTING.md) | V5.5.4 — carga + hardening |
| **PRODUCTION_READY.md** | **V5.5.5 — este checklist** |

---

## Pós go-live

1. Monitorar Command Center e alertas Prometheus nas primeiras 24h.
2. Confirmar SLOs `ok` em `/api/v1/ops/slo`.
3. Executar sync OAuth em `/analytics` após conectar canais.
4. Promover `PUBLISH_MODE` de `dry_run` para modo real **somente** após sign-off produto.

**V5 roadmap:** todas as entregas V5.0–V5.5 concluídas. Evoluções futuras → novo epic (V6) com ADR.
