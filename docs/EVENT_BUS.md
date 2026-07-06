# Event Bus (ContentOS V2.7 / Tier A1)

Central event distribution for pipeline lifecycle, agent callbacks, and real-time dashboard updates.

## Architecture

```
WorkflowEngine / Agents
        │
        ▼
 EventBusPublisher
   ├── Redis Stream  (contentos:stream:events) — replay & audit
   ├── Redis Pub/Sub (contentos:events)        — WebSocket /ws (V1 compatible)
   └── PostgreSQL    (domain_events)           — query API
```

## Event types

| Category | Examples |
|----------|----------|
| Pipeline | `pipeline.created`, `pipeline.completed` |
| Step (V1) | `step.started`, `step.completed`, `step.failed`, `step.retry` |
| Domain (V1/V2) | `research.finished`, `script.finished`, `voice.generated`, … |
| Domain (V2 media) | `clip_research.finished`, `assets.ready`, `asset_index.finished`, `takes.finished` |
| Domain (V3) | `trend_intelligence.finished`, `hook.finished`, `script_review.finished`, `emotion.finished`, `storyboard.finished`, `scene_director.finished`, `video_review.finished` |
| Creative retry | `creative_retry.started`, `creative_retry.exhausted` |

Workflow emits V1 step events. Agents emit V2 domain events on callback (e.g. `research.finished`).

### Wire format vs PascalCase (ADR-003)

**Wire format** (Redis, PG, API): `resource.action` em minúsculas.

**Aliases V3** (documentação / UI): PascalCase — resolvidos por `resolve_event_type()` / `pascal_alias()`.

| PascalCase (missão) | Wire |
|---------------------|------|
| `ResearchFinished` | `research.finished` |
| `TrendIntelligenceFinished` | `trend_intelligence.finished` |
| `HookFinished` | `hook.finished` |
| `ScriptFinished` | `script.finished` |
| `ScriptReviewFinished` | `script_review.finished` |
| `EmotionFinished` | `emotion.finished` |
| `StoryboardFinished` | `storyboard.finished` |
| `SceneDirectorFinished` | `scene_director.finished` |
| `VideoReviewFinished` | `video_review.finished` |
| `SceneFinished` | `scene.created` |
| `ClipResearchFinished` | `clip_research.finished` |
| `AssetsReady` | `assets.ready` |
| `AssetIndexFinished` | `asset_index.finished` |
| `TakesFinished` | `takes.finished` |
| `VoiceReady` | `voice.generated` |
| `SubtitleReady` | `subtitle.created` |
| `RenderReady` | `editor.finished` |
| `QualityApproved` | `quality.approved` |
| `QualityRejected` | `quality.rejected` |
| `PublisherFinished` | `publisher.finished` |
| `AnalyticsFinished` | `analytics.processed` |
| `ThumbnailCreated` | `thumbnail.created` |

### Step → domain event (`STEP_TO_DOMAIN_EVENT`)

Todos os steps de `v2-dynamic` (14) estão mapeados:

| Step | Evento |
|------|--------|
| research | `research.finished` |
| trend_intelligence | `trend_intelligence.finished` |
| hook | `hook.finished` |
| script | `script.finished` |
| script_review | `script_review.finished` |
| emotion | `emotion.finished` |
| storyboard | `storyboard.finished` |
| scene_director | `scene_director.finished` |
| video_review | `video_review.finished` |
| scene | `scene.created` |
| clip_research | `clip_research.finished` |
| asset_collector | `assets.ready` |
| asset_index | `asset_index.finished` |
| takes | `takes.finished` |
| voice | `voice.generated` |
| subtitle | `subtitle.created` |
| editor | `editor.finished` |
| quality | `quality.approved` (falha → `quality.rejected`) |
| publisher | `publisher.finished` |
| thumbnail | `thumbnail.created` |
| analytics | `analytics.processed` |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/events/recent` | Latest events (DB, fallback Redis stream) |
| GET | `/api/v1/events/pipelines/{id}` | Events for a pipeline |
| GET | `/api/v1/events/stream/info` | Redis stream metadata |

## WebSocket

Existing endpoint `ws://localhost:8000/ws` receives all events via legacy pub/sub channel `contentos:events`. No dashboard changes required for live updates.

## Environment

```env
EVENT_STREAM_KEY=contentos:stream:events
EVENT_STREAM_MAXLEN=10000
EVENT_REDIS_URL=redis://redis:6379/0
```

Uses Redis DB **0** by default (same as Celery broker).

## Integration

- **Workflow Engine** — `EventBusPublisher` replaces inline `EventPublisher`
- **Agents** — `BaseAgentHandler._callback()` publishes domain events after workflow callback
- **Gateway** — REST API + existing WebSocket hub

## Dashboard

`/events` — recent events table and stream info.

## Database

Table `domain_events` stores: `event_type`, `pipeline_id`, `project_id`, `job_id`, `agent`, `step`, `status`, `payload`, `created_at`.
