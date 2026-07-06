# Trend Forecast — Epic 10 (V4.2.4)

Evolui o step `trend_intelligence` com score numérico, crescimento esperado e recomendação de produção — sem novo step no pipeline.

## Outputs no payload

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `trend_score` | 0–100 | Força da tendência (memory + analytics + KB + learning) |
| `expected_growth` | `low` \| `moderate` \| `high` \| `very_high` | Crescimento esperado |
| `production_recommendation` | string | Ação sugerida para o criador |
| `trend_forecast_report` | object | Relatório estruturado completo |

Também embutidos em `trend_brief` para compatibilidade com `viral_engine`.

## Componentes

| Classe | Path |
|--------|------|
| `TrendForecastService` | `application/trend_forecast/service.py` |
| `heuristics` | `application/trend_forecast/heuristics.py` |
| `TrendForecastRepository` | `infrastructure/trend_forecast_repository.py` |

## Fontes do score

- Padrões e keywords do `trend_brief`
- Média de analytics insights
- `hook_patterns` e histórico em Memory
- Learning insights (`content_score`)
- Volume da Knowledge Base

## API

| Method | Path |
|--------|------|
| `POST` | `/api/v1/trend/forecast` |
| `GET` | `/api/v1/trend/forecast/pipeline/{pipeline_id}` |

## Environment

| Variable | Default |
|----------|---------|
| `TREND_FORECAST_ENABLED` | `true` |

## Evento

`trend.forecasted`

## Dashboard

`/trend-forecast`

## Tests

```bash
pytest tests/test_trend_forecast.py -q
```

## Migration

`016_v4_trend_forecast.py` — tabela `trend_forecasts`
