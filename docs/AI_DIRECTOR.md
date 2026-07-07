# AI Director — V5.2.4

Orquestra **re-run parcial** do pipeline com base nos scores agregados.

## O que analisa

| Sinal | Fonte |
|-------|--------|
| Dimensões do Content Score | `content_score_report.dimensions[]` |
| Retenção | `retention_report` / `retention_score` |
| Qualidade técnica | `quality_score` |
| SEO | `seo_package` / `seo_score` |
| Video review | `video_score` |

## Decisão (`director_decision`)

| Campo | Descrição |
|-------|-----------|
| `passed` | Scores dentro dos limiares |
| `overall_score` | Score agregado 0–100 |
| `target` | Área fraca (`hook`, `retention`, `edit`, `seo`, …) |
| `retry_from` | Step do pipeline para rebobinar |
| `action` | `advance` ou `retry` |
| `weak_signals[]` | Dimensões abaixo do mínimo |

## Mapeamento dimensão → step

| Dimensão fraca | `retry_from` |
|----------------|--------------|
| hook / viral | `hook` |
| retention | `takes` |
| cta / title | `script` |
| technical | `editor` |
| seo | `seo` |
| thumbnail | `thumbnail` |
| rhythm | `scene_director` |
| emotion | `emotion` |

Prioriza `retention_retry_plan` quando retenção falhou (V5.2.2).

## Pipeline

Step `ai_director`:

- `factory-full` — após `content_score`, antes de `content_intelligence` (31 steps)
- `v5-media-autopilot` — após `quality`, antes de `seo` (18 steps)

O workflow engine rebobina automaticamente quando `director_passed=false` (até `MAX_DIRECTOR_RETRIES`).

## API

```
POST /api/v1/director/plan
```

## Agent

`AiDirectorAgentHandler` — `services/agents-worker/handlers/ai_director.py`

## Dashboard

`/director` — preview da decisão e sinais fracos.

## Variáveis de ambiente

| Variável | Default | Descrição |
|----------|---------|-----------|
| `AI_DIRECTOR_ENABLED` | `true` | Liga step + retry |
| `AI_DIRECTOR_MIN_SCORE` | `65` | Score geral mínimo |
| `AI_DIRECTOR_DIMENSION_MIN` | `55` | Mínimo por dimensão |
| `MAX_DIRECTOR_RETRIES` | `1` | Re-runs parciais por pipeline |

## Testes

```bash
pytest tests/test_ai_director.py -q
```

