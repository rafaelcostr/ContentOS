# Production Hardening

Checklist and manifests for running ContentOS in production.

## Manifests

| Overlay / component | Purpose |
|---------------------|---------|
| `k8s/overlays/production/` | Production replicas, env, GHCR images |
| `k8s/components/ingress/` | NGINX Ingress + cert-manager TLS |
| `k8s/components/external-secrets/` | ESO template (AWS SM example) |
| `k8s/base/secret.example.yaml` | Secret template — do not commit real values |

```bash
# Production (requires KEDA + cert-manager + ESO configured)
kubectl apply -k k8s/overlays/production/
```

## Pre-flight checklist

### Secrets
- [ ] Replace `k8s/base/secret.yaml` placeholders OR use External Secrets
- [ ] Rotate `JWT_SECRET` (64+ hex chars)
- [ ] Managed PostgreSQL + Redis URLs in secrets
- [ ] MinIO/S3 credentials with least privilege

### Ingress & TLS
- [ ] Install [cert-manager](https://cert-manager.io/) + ClusterIssuer
- [ ] Update `contentos.example.com` in `k8s/components/ingress/ingress.yaml`
- [ ] Set `CORS_ORIGINS` to production dashboard URL

### Observability
- [ ] `PROMETHEUS_METRICS_ENABLED=true`, scrape `/metrics`
- [ ] `OTEL_ENABLED=true`, OTLP endpoint to Jaeger/Tempo
- [ ] Grafana dashboards — [GRAFANA.md](./GRAFANA.md)

### Workers
- [ ] KEDA installed, Redis reachable from scalers
- [ ] `kubectl apply -k k8s/overlays/autoscaling-keda/` or use production overlay

### Quality gates
- [ ] `QUALITY_MIN_SCORE=6` (technical)
- [ ] `VIDEO_REVIEW_MIN_SCORE=8` (creative) — [QUALITY.md](./QUALITY.md)

### CI/CD
- [ ] Staging: push `develop` → [DEPLOY_STAGING.md](./DEPLOY_STAGING.md)
- [ ] Production: promote tagged images from staging (manual or release workflow)

## Managed services (recommended)

| Service | Options |
|---------|---------|
| PostgreSQL | RDS, Cloud SQL, Azure Database |
| Redis | ElastiCache, Memorystore |
| Object storage | S3, GCS (MinIO compatible API) |
| LLM | Ollama on GPU node pool or cloud API via AI Gateway |

## Security

- Do not expose workflow-engine (8001) or ai-gateway (8020) publicly
- Set `PROMETHEUS_METRICS_TOKEN` if `/metrics` is on public ingress
- Enable org-scoped API keys + billing credits for tenant isolation
- Review RBAC — [RBAC.md](./RBAC.md)

## Related

- [K8S.md](./K8S.md) — base deploy & worker pools
- [DEPLOY_STAGING.md](./DEPLOY_STAGING.md) — CI staging pipeline
