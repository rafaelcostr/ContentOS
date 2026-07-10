# Growth OS — Hardening & Operations (Fase 18)

## Health check

```http
GET /api/v1/growth/health?project_id={uuid}
```

| Check | Descrição |
|-------|-----------|
| `database` | `SELECT 1` no PostgreSQL |
| `workflow_engine` | `GET {workflow_engine}/health` |
| `oauth_audit` | Todos os canais com OAuth válido (quando `project_id` informado) |

Status: `healthy` · `degraded` · `unhealthy`

## Auditoria OAuth

```http
GET /api/v1/growth/oauth-audit?project_id={uuid}
```

Status por canal: `ok` · `disconnected` · `expired` · `expiring_soon` · `missing_refresh`

Reconecte em **Publicação** (`/plugins`) quando `needs_reconnect=true`.

## Rate limits (mutações Growth)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `GROWTH_RATE_LIMIT_ENABLED` | `true` | Liga limiter em POSTs pesados |
| `GROWTH_RATE_LIMIT_PER_MINUTE` | `30` | Por usuário + ação/minuto |

Endpoints limitados: `strategy/generate`, `calendar/*/produce`, `performance/sync`, `channels/*/manager/run` (execução).

Resposta `429`: `{"error":"rate_limit","message":"...","retryable":true}`

## Tratamento de falhas

Erros Growth retornam JSON estruturado via `classify_growth_error`:

| `error` | HTTP | Retry |
|---------|------|-------|
| `validation` | 400 | não |
| `not_found` | 404 | não |
| `oauth` | 400 | não |
| `billing` | 402 | não |
| `quota` | 429 | não |
| `rate_limit` | 429 | sim |
| `workflow_unreachable` | 503 | sim |

Growth **nunca** enfileira Celery — falhas de produção vêm do Workflow Engine.

## Backup (operacional)

Tabelas Growth críticas (PostgreSQL):

- `channels` (OAuth credentials)
- `growth_channel_profiles`
- `growth_strategies`
- `growth_content_calendar`
- `growth_recommendations`
- `growth_reports`
- `growth_asset_performance`
- `channel_memory`
- `project_memory` (Brand DNA)

```bash
pg_dump -h localhost -U contentos -t channels -t growth_channel_profiles \
  -t growth_strategies -t growth_content_calendar -t growth_recommendations \
  -t growth_reports -t channel_memory -t project_memory contentos > growth_backup.sql
```

Agende backup diário + retenção 30 dias em produção.

## E2E

```bash
# In-process (CI, sem Docker)
python -m pytest tests/test_growth_e2e_flow.py tests/test_growth_hardening.py -q

# Smoke HTTP (stack local)
python scripts/e2e_growth.py
```

## Runbook rápido

1. **Growth degradado** → `GET /growth/health` → corrigir DB ou Workflow Engine
2. **Sync analytics falha** → `GET /growth/oauth-audit` → reconectar OAuth
3. **Produce 503** → verificar `workflow-engine` e filas Celery
4. **Rate limit 429** → aguardar 60s ou aumentar `GROWTH_RATE_LIMIT_PER_MINUTE` em dev
