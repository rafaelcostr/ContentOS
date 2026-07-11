# Content Sources + Media Library (ContentOS)

ContentOS **does not download** external stock video anymore.
Acquisition is owned by the **Media Collector** program, which uploads into MinIO / `own_library`.

ContentOS only **searches and consumes** local libraries for production.

## Architecture

```
Media Collector (external)
    └── POST /api/v1/assets/takes/upload  →  MinIO takes/ + Postgres assets
            └── ContentOS pipeline:
                    scene → asset_index → media_analyze → asset_search → takes → editor
```

## ContentSource protocol (local only)

| Method | Description |
|--------|-------------|
| `search(query)` | Return ranked `SourceCandidate` list from local libraries |
| `fetch(candidate_id)` | Read bytes from MinIO (local/own library) |
| `health()` | Source availability check |

## Adapters

| ID | Adapter | Description |
|----|---------|-------------|
| `local_library` | LocalLibrarySource | MinIO `takes/` prefix |
| `own_library` | OwnLibrarySource | Project assets in PostgreSQL |
| `rss` | RSSSource | RSS feed metadata (`CONTENT_SOURCE_RSS_URL`) |
| `gameplay` | GameplaySource | Filtered gameplay takes |
| `licensed_trailers` | LicensedTrailerSource | Stub for licensed catalog |
| `custom` | CustomSource | Catalog metadata only (no remote download) |

Removed: `pexels`, `pixabay`, `DownloadPipeline`, agents `clip_research` / `asset_collector`.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/content-sources` | Enabled source IDs |
| GET | `/api/v1/content-sources/health` | Health per source |
| POST | `/api/v1/content-sources/search` | Search local candidates |
| POST | `/api/v1/assets/takes/upload` | **Ingest** from Media Collector |
| GET | `/api/v1/content-sources/collections/{pipeline_id}` | Legacy collection rows |

## Environment

```env
CONTENT_SOURCES_ENABLED=local_library,own_library
ENABLE_MEDIA_ANALYZE=true
ENABLE_TAKE_RECOMMENDATION=true
```

## Package

`packages/content-sources` — `SourceManager`, `CollectionStore`, local adapters.

## Dashboard

`/content-sources` — local library health + Media Collector ingest hints.
