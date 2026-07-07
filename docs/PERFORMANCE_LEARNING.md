# Performance Learning — V5.4.2

Aprende com **métricas OAuth reais** (V5.4.1) e **retenção prevista** (V5.2.1), indexando padrões vencedores na Knowledge Base e memória do projeto.

## Fluxo

```
PlatformAnalyticsSnapshot (OAuth sync)
        +
Retention job output + Learning hooks
        ↓
PerformanceLearningService
        ↓
KB (resource_type: performance) + Memory (hook_patterns)
```

## Métricas

| Campo | Origem |
|-------|--------|
| CTR / engagement | Snapshots OAuth |
| Retenção real | Job `retention` do pipeline (match por tópico) |
| Retention delta | `completion_pct` − `hook_retention_pct` previsto |
| Tier | `high` / `medium` / `low` |

## API

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/performance-learning/process` | Analisa snapshots + indexa KB |
| GET | `/api/v1/performance-learning/insights?project_id=` | Histórico persistido |

## Integração automática

Após `POST /analytics/platforms/sync`, se `PERFORMANCE_LEARNING_AUTO_PROCESS=true`, o processamento roda em sequência.

## Variáveis de ambiente

```env
PERFORMANCE_LEARNING_ENABLED=true
PERFORMANCE_LEARNING_AUTO_INDEX_KB=true
PERFORMANCE_LEARNING_AUTO_MEMORY=true
PERFORMANCE_LEARNING_AUTO_PROCESS=false
PERFORMANCE_LEARNING_MIN_CTR=0.04
PERFORMANCE_LEARNING_MIN_VIEWS=50
```

## Dashboard

`/learning` — botão **Performance Learning → KB**, lista de insights OAuth e **Próximo vídeo** (recomendações).

## Loop de recomendação (fase 7.5)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/projects/{project_id}/recommendations` | Agrega performance + learning + comentários |

Fonte: `contentos_intelligence.application.recommendations.build_project_recommendations`.

## Testes

```powershell
pytest tests/test_performance_learning.py tests/test_recommendations.py -q
```

## Próximo

**V5.4.3** — Comment Analyzer.
