# Content Score — Epic 9 (V4.1.2)

Nota unificada **0–100** que compõe sinais V3/V4 sem substituir `quality_score` nem `video_review`.

## Overview

`ContentScoreService` agrega 10 dimensões ponderadas:

| Dimensão | Peso | Fonte |
|----------|------|-------|
| Hook | 15% | `viral_report.hook_score` |
| Retenção | 15% | `viral_report.retention_prediction` |
| Emoção | 10% | `emotion.overall` (0–10 → 0–100) |
| CTA | 10% | `viral_report.cta_score` / script / DNA |
| SEO | 10% | heurística preview (V4.2 multi-content) |
| Título | 10% | vencedor A/B ou `script.title` |
| Thumbnail | 10% | vencedor A/B |
| Técnica | 10% | `quality_score` / `video_score` (0–10 → 0–100) |
| Originalidade | 5% | inverso similaridade KB |
| Ritmo | 5% | `viral_report.rhythm_score` |

## Modos

| Modo | Quando |
|------|--------|
| `preview` | Step `content_intelligence` (pré-render) |
| `full` | Payload com `quality_score` ou `video_score` |

## Payload

```json
{
  "content_score_report": {
    "total_score": 78.5,
    "grade": "bom",
    "mode": "preview",
    "summary": "Boa base — ajustes pontuais podem elevar o resultado. Nota 79/100 (bom).",
    "dimensions": [
      { "name": "hook", "score": 80, "weight": 0.15, "source": "viral_report.hook_score" }
    ]
  }
}
```

## API

```http
POST /api/v1/content-score/score
{
  "project_id": "...",
  "topic": "GTA 6",
  "payload": { "emotion": { "overall": 8 } },
  "full_pipeline": true
}
```

`full_pipeline: true` executa reuse + viral + A/B + score (mesmo fluxo do step).

## Eventos

- `content_score.computed` (alias `ContentScoreComputed`)

## Environment

| Variable | Default |
|----------|---------|
| `CONTENT_SCORE_ENABLED` | `true` |
| `CONTENT_SCORE_WEIGHTS` | JSON opcional — sobrescreve pesos |

## Dashboard

`/content-score` — calcular nota por projeto.

## Tests

```bash
pytest tests/test_content_score.py -q
```
