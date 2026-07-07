# KEDA em produção — V5.5.2

Autoscaling de workers Celery por profundidade de fila Redis (KEDA `redis` scaler).

## Pools V5 (novos)

| Deployment | Pool | Filas | Concurrency | KEDA triggers |
|------------|------|-------|-------------|---------------|
| `agents-worker-v5-quality` | v5-quality | retention, seo, ai_director, creative_memory, quality, video_review, auto_retry, content_score | 2 | retention, seo, ai_director, creative_memory |
| `agents-worker-v5-media` | v5-media | clip_research, asset_collector, asset_index, media_analyze, asset_search | 2 | media_analyze, asset_collector, clip_research |

Filas de qualidade foram **removidas** do pool `general` para evitar contenção e permitir escala independente.

## Pool general (atualizado)

Filas restantes: `scene`, `takes`, `voice`, `subtitle`, `knowledge_base`, `publisher`, `thumbnail`, `analytics`, `learning`, `content_intelligence`, `multi_content`, `multi_content_video`.

KEDA escala pelo **máximo** entre triggers: `publisher`, `analytics`, `learning`, `multi_content`.

## Limites por ambiente

| ScaledObject | Base (min/max) | Staging (max) | Production (min/max) |
|--------------|----------------|---------------|----------------------|
| v5-quality | 1 / 10 | 1 / 3 | 2 / 12 |
| v5-media | 1 / 8 | 1 / 3 | 2 / 10 |
| general | 2 / 10 | 1 / 4 | 2 / 12 |

## Deploy

```bash
# KEDA (uma vez por cluster)
kubectl apply -f https://github.com/kedacore/keda/releases/download/v2.16.0/keda-2.16.0.yaml

# Produção (inclui overlay autoscaling-keda + patches V5)
kubectl apply -k k8s/overlays/production/

# Verificar scalers
kubectl -n contentos get scaledobject
kubectl -n contentos describe scaledobject agents-worker-v5-quality-scaler
```

## Arquivos

| Arquivo | Conteúdo |
|---------|----------|
| `k8s/base/agents-worker-pools-v5.yaml` | Deployments V5 |
| `k8s/components/keda/scaledobjects-v5.yaml` | ScaledObjects V5 |
| `k8s/components/keda/scaledobjects.yaml` | Scalers E4 + general multi-trigger |
| `k8s/overlays/production/patch-resources-v5.yaml` | Réplicas e limites prod |

## Local (Docker Compose)

Espelho em `docker/docker-compose.scale.yml` — serviços `agents-v5-quality` e `agents-v5-media`.

## Operação

- **Scale-up:** quando `listLength` de qualquer trigger é excedido, KEDA aumenta réplicas do deployment alvo.
- **Scale-down:** após `cooldownPeriod` (120–180s) sem carga acima do limiar.
- **Redis:** endereço `redis:6379` (service in-cluster); `databaseIndex: 0` (broker Celery).

Ver também [K8S.md](./K8S.md) e [PRODUCTION_HARDENING.md](./PRODUCTION_HARDENING.md).
