# Command Center — V5.5.1

Evolução do **Executive Dashboard** (`/executive`) para visão unificada **V4 + V5**.

## Página

`/executive` — **Command Center** com KPIs, alertas operacionais e cards V4/V5.

## API

| Method | Path | Descrição |
|--------|------|-----------|
| `GET` | `/api/v1/executive/summary?project_id=` | Agrega V4 + V5 |

### Campos V5.5.1 (aditivos)

| Campo | Fonte |
|-------|--------|
| `factory_batches_total` | `content_batches` |
| `factory_batches_running` | lotes running/pending approval |
| `factory_pending_approval` | lotes aguardando publicação |
| `platform_snapshots` | `platform_analytics_snapshots` |
| `performance_insights` | `performance_learning_insights` |
| `comment_insights` | `comment_analysis_insights` |
| `community_drafts_pending` | `community_reply_drafts` status=draft |
| `oauth_channels_connected` | `channels` com OAuth |
| `alerts[]` | regras operacionais |
| `v5_modules[]` | cards Factory, Retention, SEO, Director, etc. |

## Alertas automáticos

- Lotes aguardando aprovação de publicação
- Rascunhos de comunidade pendentes
- OAuth sem sync de métricas
- Pipelines sem canais OAuth
- **SLO breach** (infra, workers, backlog, taxa de sucesso 24h) — V5.5.3

## SLO (V5.5.3)

O endpoint `/executive/summary` inclui `slo_items[]` com estado por SLO de plataforma.
API dedicada: `GET /api/v1/ops/slo` · runbooks: `GET /api/v1/ops/runbooks`.

Ver [SLO_ALERTS_RUNBOOKS.md](./SLO_ALERTS_RUNBOOKS.md).

## Módulos V5 (cards)

Content Factory, Retention, SEO, AI Director, Creative Memory, OAuth Analytics, Performance Learning, Comment Analyzer, Community Agent, Voice Studio.

## Componentes

| Classe | Path |
|--------|------|
| `ExecutiveSummaryService` | `application/executive/summary_service.py` |
| `build_command_center_alerts` | `application/executive/command_center.py` |

## Testes

```powershell
pytest tests/test_executive_dashboard.py -q
```

## Base V4

Ver [EXECUTIVE_DASHBOARD.md](./EXECUTIVE_DASHBOARD.md).
