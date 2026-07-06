# Asset Manager V2 (ContentOS V2.11)

Extended asset indexing on top of MinIO storage — search, tags, SHA-256 dedup.

## Features

| Feature | Description |
|---------|-------------|
| Hash index | `sha256` column on `assets` table |
| Dedup on upload | `upload_take` returns existing asset if hash matches |
| Tags | JSON array on asset — theme, label, custom tags |
| Search | Query by key, category, tag |
| Version field | `version` + `parent_asset_id` for future versioning |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/assets/search` | Advanced search (see filters below) |
| GET | `/api/v1/assets/{id}/preview` | Presigned MinIO URL (`expires`, default 3600s) |
| GET | `/api/v1/assets/{id}/content` | Authenticated byte stream (dashboard preview) |
| POST | `/api/v1/assets/{id}/tags` | Add tags `{ "tags": ["action"] }` |
| GET | `/api/v1/assets/index/stats` | Index + storage stats |

### Preview (Tier A3)

- **`/preview`** — URL assinada MinIO; host interno (`minio:9000`) reescrito para `MINIO_PUBLIC_ENDPOINT` (`localhost:9000`).
- **`/content`** — stream autenticado (Bearer); usado pelo dashboard para evitar CORS do MinIO.
- Dashboard `/assets` carrega imagem/vídeo/áudio no detalhe e oferece link da URL assinada.

### Search filters (Tier A2)

| Param | Description |
|-------|-------------|
| `q` | Free text (key, content-type, theme, game, character, motion, color, objects, labels) |
| `category` | Asset category (`takes`, `renders`, …) |
| `tag` | Exact tag match |
| `theme` | Theme / topic |
| `game` | Game title |
| `character` | Character name |
| `motion` | Camera / motion hint |
| `color` | Dominant / palette color |
| `objects` | Objects / keywords |
| `limit` | Max results (default 50, max 200) |

Metadata is stored in `assets.metadata` (JSON) and mirrored as facet tags (`theme:GTA 6`, `object:car`, …).

## Package

| Class | Path |
|-------|------|
| `AssetManager` | `domain/asset_manager.py` (MinIO) |
| `AssetPipelineService` | `application/asset_pipeline_service.py` — store + PG persist + dedup |
| `AssetIndexService` | `application/asset_index_service.py` — search, tags, hash |
| `PgAssetRepository` | `infrastructure/pg_asset_repository.py` |

## Integration

- **Asset Collector** — `store_and_persist` (MinIO + `assets` table, global SHA-256 dedup)
- **Asset Index** — tags `indexed`, `pipeline:{id}`
- **Takes upload** — skips duplicate bytes
- **Dashboard** `/assets` — biblioteca, busca, tags
- **Dashboard** `/storage` — upload de takes + stats

## Dashboard

| Route | Module |
|-------|--------|
| `/assets` | Biblioteca indexada (busca, tags, hash, versão) |
| `/storage` | Upload takes + stats MinIO |
| `/ai-gateway` | Gateway health + provider routing |
| `/clip-research` | Agent stats + recent searches |
| `/asset-collector` | Collection stats + dedup index |

