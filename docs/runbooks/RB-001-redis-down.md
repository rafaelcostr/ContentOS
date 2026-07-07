# RB-001 — Redis indisponível

**Alerta:** `ContentOSRedisDown` · **SLO:** `redis-availability`

## Sintomas

- `contentos_redis_up == 0`
- Workers Celery não consomem filas
- Gateway reporta Redis `unhealthy` em `/api/v1/metrics/infrastructure`

## Diagnóstico

```bash
kubectl -n contentos get pods -l app=redis
redis-cli -u $REDIS_URL ping
curl -s http://gateway:8000/metrics | grep contentos_redis_up
```

## Ações

1. Verificar pod/serviço Redis no cluster ou instância managed.
2. Confirmar `REDIS_URL` / `CELERY_BROKER_URL` no ConfigMap `contentos-config`.
3. Reiniciar gateway após Redis voltar: `kubectl -n contentos rollout restart deployment/gateway`
4. Validar: `contentos_redis_up == 1` e filas diminuindo.

## Escalação

Se Redis managed (ElastiCache, Memorystore): abrir ticket com provider + logs do gateway.
