# Unified Marketplace (V3 Tier D3)

Single catalog for **plugins**, **agents**, and **workflows** — local + optional remote feed.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/marketplace` | Full unified catalog |
| `GET` | `/api/v1/marketplace?type=plugin` | Filter by type |

Response:

```json
{
  "summary": {"plugin": 6, "agent": 20, "workflow": 4, "total": 32},
  "remote_configured": false,
  "items": [
    {
      "id": "agent:research",
      "type": "agent",
      "name": "research",
      "description": "...",
      "queue": "contentos.research",
      "source": "local"
    }
  ]
}
```

Item types: `plugin`, `agent`, `workflow`.

Sources: `local`, `builtin`, `custom`, `remote`.

## Remote catalog

Set `MARKETPLACE_REMOTE_URL` to a JSON URL:

```json
{
  "items": [
    {
      "type": "workflow",
      "name": "community-pack",
      "description": "...",
      "steps": ["research", "script", "publisher"]
    }
  ]
}
```

Fallback file: `{PLUGINS_ROOT}/marketplace/unified_remote.json` (shipped demo).

Cache TTL: `MARKETPLACE_REMOTE_CACHE_SECONDS` (default 300).

## Dashboard

**Observabilidade → Marketplace** (`/marketplace`) — filtros por tipo, cards unificados.

Plugin install/enable remains on `/plugins` (platform admin).

## Related

- [PLUGIN_MARKETPLACE.md](./PLUGIN_MARKETPLACE.md) — plugin install API
- [WORKFLOW_BUILDER.md](./WORKFLOW_BUILDER.md) — custom org workflows appear in catalog
