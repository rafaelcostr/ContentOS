# Plugin Marketplace (ContentOS V2.9)

Extensible publish plugins with install/enable lifecycle — without modifying core code.

## Architecture

```
plugins/marketplace/     # Catalog + plugin packages (telegram, discord, wordpress)
plugins/installed/       # Copied on install
plugins/state/           # JSON fallback when DB unavailable
installed_plugins (DB)   # Install + enable state
```

Builtin plugins (`tiktok`, `youtube`, `instagram`) ship in `packages/shared` and are always available.

## Plugin manifest (`plugin.yaml`)

```yaml
name: telegram
version: 1.0.0
hooks: [post_publish]
entrypoint: telegram_plugin.TelegramPlugin
platform: telegram
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/plugins` | Installed plugins + config |
| GET | `/api/v1/plugins/marketplace` | Full catalog with install status |
| POST | `/api/v1/plugins/install` | Install plugin `{ "name": "telegram" }` |
| DELETE | `/api/v1/plugins/{name}` | Uninstall (not builtins) |
| POST | `/api/v1/plugins/{name}/enable` | Enable/disable `{ "enabled": true }` |

## Available plugins

| Plugin | Type | Description |
|--------|------|-------------|
| tiktok | builtin | TikTok vertical video |
| youtube | builtin | YouTube Shorts |
| instagram | builtin | Instagram Reels |
| telegram | marketplace | Telegram channel post |
| discord | marketplace | Discord webhook embed |
| wordpress | marketplace | WordPress REST API post |

## Environment

```env
PLUGINS_ROOT=/app/plugins
ENABLED_PLATFORMS=tiktok,youtube,instagram
PUBLISH_MODE=dry_run
```

When plugins are enabled via API, DB state overrides `ENABLED_PLATFORMS`.

## Credentials (live mode)

```json
{
  "telegram": {"bot_token": "...", "chat_id": "..."},
  "discord": {"webhook_url": "https://discord.com/api/webhooks/..."},
  "wordpress": {"site_url": "https://blog.example.com", "username": "...", "app_password": "..."}
}
```

Set via `PLATFORM_CREDENTIALS_JSON` or `POST /api/v1/channels`.

## Package

`packages/plugins-core` — discovery, installer, marketplace, dynamic loader.

## Dashboard

`/plugins` — marketplace catalog, install/enable actions, active plugins.
