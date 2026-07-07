# RB-002 — PostgreSQL indisponível

**Alerta:** `ContentOSPostgresDown` · **SLO:** `postgres-availability`

## Sintomas

- `contentos_postgres_up == 0`
- API retorna 500 em rotas com DB
- Command Center sem KPIs

## Diagnóstico

```bash
kubectl -n contentos logs deployment/gateway --tail=50
psql $DATABASE_URL -c "SELECT 1"
curl -s http://gateway:8000/metrics | grep contentos_postgres_up
```

## Ações

1. Verificar RDS/Cloud SQL ou pod Postgres.
2. Validar `DATABASE_URL` em secrets (`contentos-secrets`).
3. Checar conexões máximas e locks: `SELECT count(*) FROM pg_stat_activity;`
4. Após recuperação, confirmar latência < 500ms no SLO.

## Escalação

DBA / provider managed DB se indisponibilidade > 15 min.
