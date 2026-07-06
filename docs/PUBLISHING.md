# Publishing — Live mode + OAuth (Tier D4)

ContentOS supports **dry-run** publishing by default and **live** publishing when `PUBLISH_MODE=live` and valid OAuth tokens exist on project channels.

## Flow

1. Configure OAuth client credentials in `.env` (YouTube/Google, TikTok, or Meta/Instagram).
2. In the dashboard (**Publicação → Conectar plataformas**), select a project and start OAuth for each platform.
3. Tokens are stored in the `channels.credentials` JSON column.
4. The **publisher** agent loads credentials from the database (with env fallback) and refreshes expired tokens when possible.
5. Set `PUBLISH_MODE=live` on the gateway and agents-worker to perform real uploads.

## Environment variables

```env
PUBLISH_MODE=dry_run
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
- Live mode requires both env flag and valid `access_token` per platform.
- OAuth state is a short-lived JWT signed with `JWT_SECRET`.

## Apply

```powershell
docker compose -f docker/docker-compose.yml up -d --build gateway agents-worker dashboard
```

No new database migration is required; credentials live in the existing `channels.credentials` JSON column.
