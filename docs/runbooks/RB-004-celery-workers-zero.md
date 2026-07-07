# RB-004 — Sem workers Celery

**Alerta:** `ContentOSCeleryWorkersZero` · **SLO:** `celery-workers`

## Sintomas

- `contentos_celery_workers < 1`
- Filas crescendo, pipelines em `running` sem progresso

## Diagnóstico

```bash
kubectl -n contentos get pods -l app=agents-worker
kubectl -n contentos get scaledobject
celery -A contentos_agents.worker inspect ping  # de um pod worker
```

## Ações

1. Verificar deployments: `agents-worker-research`, `script`, `editor`, `general`, `v5-quality`, `v5-media`.
2. Checar KEDA: `kubectl -n contentos describe scaledobject agents-worker-general-scaler`
3. Ver logs de crash: `kubectl -n contentos logs deployment/agents-worker-general --tail=100`
4. Escalar manualmente se KEDA falhar: `kubectl -n contentos scale deployment agents-worker-general --replicas=2`

Ver [KEDA_PRODUCTION.md](../KEDA_PRODUCTION.md).
