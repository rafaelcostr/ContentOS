# Analytics AI + Thumbnail (ContentOS V2.8)

Post-publication AI analysis and optional thumbnail generation — **async**, never blocks the V1 9-step pipeline.

## Flow

```
Pipeline completes (publisher done)
        │
        ├── ENABLE_THUMBNAIL=true  → Celery contentos.thumbnail
        └── ENABLE_ANALYTICS_AI=true → Celery contentos.analytics
```

Both agents use `AsyncV2AgentHandler` — no workflow callback, only event bus + persistence.

## Analytics AI

- Collects metrics from publication payload (views/likes when available, else estimated)
- Correlates with `models_used` and `prompts_used`
- LLM analysis via `analytics.md` prompt
- Stores result in `analytics_insights` table
- Optional: apply suggestions to Memory Manager (`ANALYTICS_AUTO_APPLY_MEMORY=true`)

### Analysis JSON shape

```json
{
  "summary": "...",
  "strengths": ["..."],
  "weaknesses": ["..."],
  "suggestions": ["..."],
  "recommended_prompt_tweaks": [{"hook_style": "..."}],
  "score": 75
}
```

## Thumbnail

- Optional concept via `thumbnail.md` (text LLM)
- Generates 1080×1920 JPEG via `LocalThumbnailProvider`:
  - Frame extract from render (ffmpeg) + text overlay (Pillow), or
  - Colored placeholder when no render
- Stores in MinIO `thumbs/` and links `videos.thumb_asset_id`

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/analytics/insights` | Recent AI insights |
| GET | `/api/v1/analytics/insights/{pipeline_id}` | Insight for pipeline |
| POST | `/api/v1/analytics/insights/{pipeline_id}/apply` | Apply suggestions to memory |

## Environment

```env
ENABLE_ANALYTICS_AI=true
ENABLE_THUMBNAIL=false
ANALYTICS_AUTO_APPLY_MEMORY=false
```

## Events

- `analytics.processed` — Analytics AI finished
- `thumbnail.created` — Thumbnail stored

## Dashboard

`/analytics` — includes **AI Insights** section with scores and apply-to-memory action.

## Package

`packages/analytics-ai` — `AnalyticsService`, insight repository, memory integration.
