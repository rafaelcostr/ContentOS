# Publishing — Live mode + OAuth (Tier D4)

ContentOS supports three publish modes and blocks **live** uploads when audiovisual QA fails (unless overridden by factory approval).

## Modes

| Mode | Behavior |
|------|----------|
| `dry_run` | Metadata preview only — no external API uploads |
| `prepare_only` | Formats platform payloads without uploading |
| `live` | Real uploads when OAuth credentials exist |

Promote gradually: `dry_run` → `prepare_only` → `live`.

## QA gate (phase 5 + 6)

When `PUBLISH_REQUIRE_QA=true` (default in `APP_ENV=production`), **live** publish is blocked unless:

- `quality_passed`
- `video_review_passed`
- `retention_passed` (when present)

Dry-run still produces `publication.json` for review. Failed live attempts emit `status: blocked_qa`.

## Flow

1. Configure OAuth client credentials in `.env` (YouTube/Google, TikTok, or Meta/Instagram).
2. In the dashboard (**Publicação → Conectar plataformas**), select a project and start OAuth for each platform.
3. Tokens are stored in the `channels.credentials` JSON column.
4. The **publisher** agent loads credentials from the database (with env fallback) and refreshes expired tokens when possible.
5. Set `PUBLISH_MODE=live` on the gateway and agents-worker to perform real uploads.

## Environment variables

```env
PUBLISH_MODE=dry_run
PUBLISH_REQUIRE_QA=
ENABLED_PLATFORMS=tiktok,youtube,instagram
OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/oauth/callback
DASHBOARD_URL=http://localhost:3000

# YouTube (Google Cloud OAuth)
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=

# TikTok Developer Portal
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=

# Meta / Instagram
META_APP_ID=
META_APP_SECRET=

# Optional manual fallback (merged under DB OAuth tokens)
PLATFORM_CREDENTIALS_JSON={}
```

Register the redirect URI in each provider console:

- Google: `OAUTH_REDIRECT_URI`
- TikTok: same URI in app settings
- Meta: Valid OAuth Redirect URIs in Facebook Login

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/oauth/platforms` | OAuth availability per platform |
| POST | `/api/v1/oauth/{platform}/start` | Start OAuth (`project_id`, optional `channel_id`) |
| GET | `/api/v1/oauth/callback` | Provider callback (redirects to dashboard) |
| GET | `/api/v1/publish/status?project_id=` | Publish mode + connection status |
| GET | `/api/v1/publish/attempts?project_id=` | Audit log (`platform_publications`) |
| GET | `/api/v1/publish/channels?project_id=` | Project channels with OAuth status |
| POST | `/api/v1/publish/channels/{id}/disconnect` | Clear channel credentials |

Existing channel CRUD remains at `/api/v1/channels`.

## Credential merge

The publisher merges credentials as:

1. `PLATFORM_CREDENTIALS_JSON` from environment
2. Active project channels from PostgreSQL (**DB wins** on conflicts)

Token refresh uses `refresh_token` when `expires_at` is near or past.

## Safety

- Default `PUBLISH_MODE=dry_run` — no external uploads.
- Live mode requires env flag, QA gate (when enforced), and valid `access_token` per platform.
- Instagram live uses `render_public_url` (MinIO presigned + `MINIO_PUBLIC_ENDPOINT`) when `video_url` is not set manually.
- OAuth state is a short-lived JWT signed with `JWT_SECRET`.

## Dashboard

- **Publicação → Conectar plataformas** (`/plugins`): OAuth, modo de publish e histórico de tentativas (`PublishAttempts`).
- Após OAuth, o dashboard invalida `publish-status`, `publish-channels` e `publish-attempts`.

## Pipeline order (breaking change)

A partir da fase de retenção pós-render, a ordem do factory é **`quality` → `retention` → `video_review`** (antes era `retention` → `quality`). Pipelines **em andamento** criados com a ordem antiga precisam ser recriados. Regenerar `docs/FACTORY_TRUTH_TABLE.md` com `python scripts/generate_factory_truth_table.py` após mudanças de estágio.

## Apply

```powershell
cd packages/database
python -m alembic -c alembic.ini upgrade head
docker compose -f docker/docker-compose.yml up -d --build gateway agents-worker dashboard
```

Migration **022** creates `platform_publications`. Run alembic from `packages/database` (not the repo root).

No new database migration is required; credentials live in the existing `channels.credentials` JSON column.
