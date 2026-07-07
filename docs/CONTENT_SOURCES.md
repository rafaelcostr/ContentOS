# Content Sources + Clip Pipeline (ContentOS V2.10)

Pluggable media discovery for B-roll — powers **Clip Research** and **Asset Collector** without breaking the V1 9-step pipeline.

## Architecture

```
scene completes
    └── ENABLE_V2_CLIP_PIPELINE=true
            ├── clip_research (search sources + LLM refine)
            └── asset_collector (fetch, dedup, store)
                    └── takes agent uses collected assets
```

## ContentSource protocol

| Method | Description |
|--------|-------------|
| `search(query)` | Return ranked `SourceCandidate` list |
| `fetch(candidate_id)` | Download `SourceAsset` bytes |
| `health()` | Source availability check |

## Adapters

| ID | Adapter | Description |
|----|---------|-------------|
| `local_library` | LocalLibrarySource | MinIO `takes/` prefix |
| `own_library` | OwnLibrarySource | Project assets in PostgreSQL |
| `pexels` | PexelsSource | Pexels Video API (V5.0 — royalty_free) |
| `pixabay` | PixabaySource | Pixabay Video API (V5.0 — royalty_free) |
| `rss` | RSSSource | RSS feed metadata (`CONTENT_SOURCE_RSS_URL`) |
| `gameplay` | GameplaySource | Filtered gameplay takes |
| `licensed_trailers` | LicensedTrailerSource | Stub for licensed catalog |
| `custom` | CustomSource | `CONTENT_SOURCE_CUSTOM_JSON` entries |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/content-sources` | Enabled source IDs |
| GET | `/api/v1/content-sources/health` | Health per source |
| POST | `/api/v1/content-sources/search` | Search candidates |
| GET | `/api/v1/content-sources/collections/{pipeline_id}` | Clip research + collected assets |

## Environment

```env
ENABLE_V2_CLIP_PIPELINE=false
CONTENT_SOURCES_ENABLED=local_library,own_library,pexels,pixabay
PEXELS_API_KEY=
PIXABAY_API_KEY=
MEDIA_MAX_DOWNLOAD_MB=50
MEDIA_ALLOWED_LICENSES=royalty_free,creative_commons
MEDIA_COLLECT_TOP_N=3
```

See [MEDIA_PIPELINE.md](./MEDIA_PIPELINE.md) for V5.0 acquisition details.

## Database

Table `pipeline_asset_collections` stores `candidates`, `assets`, and `status` per pipeline.

## Package

`packages/content-sources` — `SourceManager`, `CollectionStore`, adapters.

## Dashboard

`/content-sources` — enabled sources, health, pipeline config hints.

## Agents

- `clip_research` — searches sources per scene, optional LLM via `clip_research.md`
- `asset_collector` — fetches top candidates, SHA-256 dedup, stores in MinIO
- `takes` — prefers V2 collected assets when available
