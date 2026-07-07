# ContentOS — Kubernetes



Manifests em `k8s/` — Kustomize base + overlays.



## Componentes (base)



| Recurso | Réplicas default |

|---------|------------------|

| gateway | 2 |

| workflow-engine | 1 |

| ai-gateway | 1 |

| dashboard | 2 |

| **agents-worker-research** | 1 |

| **agents-worker-script** | 1 |

| **agents-worker-editor** | 1 |

| **agents-worker-general** | 2 |
| **agents-worker-v5-quality** | 1 |
| **agents-worker-v5-media** | 1 |



Infra externa esperada: PostgreSQL, Redis, MinIO, Ollama, Piper, Whisper.



---



## Worker pools & autoscaling (Tier E4)



Workers are split by Celery queue group (mirrors `docker-compose.scale.yml`):



| Pool | Queues | Concurrency |

|------|--------|-------------|

| research | `contentos.research` | 2 |

| script | script, script_review, hook | 2 |

| editor | `contentos.editor` | 4 |

| general | scene, takes, voice, subtitle, publisher, analytics, learning, multi_content, … | 2 |
| **v5-quality** | retention, seo, ai_director, creative_memory, quality, video_review, … | 2 |
| **v5-media** | clip_research, asset_collector, media_analyze, asset_search, … | 2 |



### Overlay: KEDA (queue depth — recommended)



Scales each pool when Redis list length exceeds threshold.



```bash

# Install KEDA once per cluster

kubectl apply -f https://github.com/kedacore/keda/releases/download/v2.16.0/keda-2.16.0.yaml



kubectl apply -k k8s/overlays/autoscaling-keda/

```

Detalhes dos pools V5 e limites de produção: [KEDA_PRODUCTION.md](./KEDA_PRODUCTION.md).



### Overlay: CPU HPA (no KEDA)



```bash

kubectl apply -k k8s/overlays/autoscaling-cpu/

```



---



## Staging (Tier E5)



```bash

kubectl apply -k k8s/overlays/staging/

```



Namespace `contentos-staging`, reduced replicas, `APP_ENV=staging`.



CI/CD: see [DEPLOY_STAGING.md](./DEPLOY_STAGING.md).

Production: [PRODUCTION_HARDENING.md](./PRODUCTION_HARDENING.md).

```bash
kubectl apply -k k8s/overlays/production/
```



---



## Deploy production



```bash

kubectl apply -f k8s/base/secret.yaml   # valores reais

kubectl apply -k k8s/overlays/autoscaling-keda/

kubectl -n contentos get pods

```



---



## Build & push imagens



```bash

docker build -f docker/Dockerfile.gateway -t your-registry/contentos/gateway:v1 .

docker build -f docker/Dockerfile.workflow -t your-registry/contentos/workflow-engine:v1 .

docker build -f docker/Dockerfile.agent -t your-registry/contentos/agents-worker:v1 .

docker build -f docker/Dockerfile.ai-gateway -t your-registry/contentos/ai-gateway:v1 .

docker build -f apps/dashboard/Dockerfile -t your-registry/contentos/dashboard:v1 apps/dashboard

```



Atualize `images:` no overlay ou use `kustomize edit set image`.



---



## Scale manual



```bash

kubectl -n contentos scale deployment agents-worker-editor --replicas=3

kubectl -n contentos get scaledobject

```



---



## Produção — checklist



- [ ] Secrets com valores reais (JWT, Postgres, MinIO)

- [ ] Ingress + TLS (cert-manager)

- [ ] PostgreSQL / Redis / MinIO managed

- [ ] KEDA instalado (autoscale por fila)

- [x] Monitoring — [PROMETHEUS.md](./PROMETHEUS.md), [GRAFANA.md](./GRAFANA.md)

- [x] Tracing — [OPENTELEMETRY.md](./OPENTELEMETRY.md)

- [x] Go-live checklist — [PRODUCTION_READY.md](./PRODUCTION_READY.md)

