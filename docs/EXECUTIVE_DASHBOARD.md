# Executive Dashboard — Epic 12 (V4.3.2)

Visão executiva unificada com dados live de todos os módulos V4.

## Página

`/executive` — dashboard com KPIs e cards linkando cada módulo.

## API

| Method | Path | Descrição |
|--------|------|-----------|
| `GET` | `/api/v1/executive/summary?project_id=` | Agrega métricas V4 do projeto |

### Resposta (resumo)

- Contagens: pipelines, KB, learning, grafo, A/B
- Médias: content score, viral score (via learning insights)
- Último trend forecast
- DNA preview + hook patterns
- `modules[]` — status por módulo com link para página detalhe

## Módulos agregados

| Módulo | Página | Fonte |
|--------|--------|-------|
| Viral Intelligence | `/viral` | avg viral (learning) |
| Knowledge Base | `/knowledge` | `knowledge_entries` |
| Project DNA | `/memory` | `ProjectMemory` |
| Content Score | `/content-score` | avg learning `content_score` |
| A/B Testing | `/ab-testing` | `ab_variants` |
| Trend Forecast | `/trend-forecast` | `trend_forecasts` |
| Specialists | `/specialists` | catalog |
| Learning Engine | `/learning` | `learning_insights` |
| Smart Reuse | `/knowledge` | KB + reuse API |
| Content Graph | `/content-graph` | `content_relations` |
| Multi Content | `/multi-content` | pipelines completos |

## Componentes

| Classe | Path |
|--------|------|
| `ExecutiveSummaryService` | `application/executive/summary_service.py` |
| `ExecutiveSummary` | `domain/executive_summary.py` |

## Tests

```bash
pytest tests/test_executive_dashboard.py -q
```

## Critério V4.3

Grafo consultável + dashboard com dados live das APIs V4 — **concluído**.

## Fase V4

Com V4.3.2, o roadmap V4.0–V4.3 está **completo**.
