# Viral Intelligence Engine (ContentOS V4 — Epic 1)

Relatório único de viralização **antes das cenas** — compõe sinais dos agentes V3 sem novas chamadas LLM.

## Componentes

| Classe | Função |
|--------|--------|
| `HookAnalyzer` | `analyze_hook()` — gancho e estilo |
| `EmotionPredictor` | `analyze_emotion()` — scores do step `emotion` |
| `RhythmAnalyzer` | `analyze_rhythm()` — cenas + `director_plan` |
| `SceneAnalyzer` | `analyze_scenes()` — storyboard + cobertura |
| `TrendMatcher` | `analyze_trend()` — `trend_context` / `trend_brief` |
| `RetentionPredictor` | `predict_retention()` — heurística 0–100 |
| `ViralityScore` | `compute_viral_score()` — agregação ponderada |
| `PayloadViralityScorer` | `IViralityScorer` — orquestra analisadores |
| `ContentIntelligenceAgentHandler` | Step `content_intelligence` (reuse + viral + A/B) |

## Template `v4-intelligence`

17 steps — igual `v3-quality` com `content_intelligence` após `emotion`:

```
… → emotion → content_intelligence → scene → …
```

Opt-in. `v1-default`, `v2-dynamic`, `v3-quality` **inalterados**.

## Payload do step

```json
{
  "viral_report": {
    "viral_score": 78.5,
    "retention_prediction": 72.0,
    "recommendations": ["..."],
    "hook_score": 80,
    "emotion_score": 75,
    "rhythm_score": 85,
    "scene_score": 70,
    "cta_score": 62
  },
  "reuse_suggestions": [],
  "ab_test": { "dimensions": [], "winners": {} },
  "content_score_report": { "total_score": 0, "grade": "", "mode": "preview", "dimensions": [] }
}
```

Ver [AB_TESTING.md](./AB_TESTING.md) e [CONTENT_SCORE.md](./CONTENT_SCORE.md).

## API

```http
POST /api/v1/viral/analyze
{
  "project_id": "...",
  "topic": "GTA 6",
  "payload": { "emotion": { "overall": 8, "retention": 7 }, "selected_hook": { "hook_text": "..." } },
  "include_reuse": true
}
```

## Evento

`content_intelligence.finished` (alias `ContentIntelligenceFinished`)

## Fila Celery

`contentos.content_intelligence`
