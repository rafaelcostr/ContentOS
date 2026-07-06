# API Keys (V3 Tier C5)

Organization-scoped public API keys for programmatic access to ContentOS.

## Authentication

Send the key in the `X-API-Key` header:

```http
GET /api/v1/projects
X-API-Key: cos_a1b2c3d4e5f6_<secret>
```

JWT (`Authorization: Bearer …`) and API keys are mutually exclusive on management routes — creating or revoking keys requires JWT.

## Scopes

| Scope | Effective role | Typical use |
|-------|----------------|-------------|
| `read` | viewer | List projects, pipelines, assets |
| `write` | editor | Create pipelines, upload assets |

API keys are locked to the organization they were created in. If you send `X-Organization-Id`, it must match that org.

## Rate limiting

Each key has `rate_limit_per_minute` (default from `API_KEY_DEFAULT_RATE_LIMIT`, usually 120). Excess requests return `429`.

Redis (`REDIS_URL` or `API_KEY_REDIS_URL`) is used when available; otherwise an in-memory fallback applies per process.

## Management (org admin, JWT only)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/organizations/{org_id}/api-keys` | List active keys (prefix only) |
| `POST` | `/api/v1/organizations/{org_id}/api-keys` | Create key — raw value returned once |
| `DELETE` | `/api/v1/organizations/{org_id}/api-keys/{key_id}` | Revoke key |

### Create body

```json
{
  "name": "CI deploy",
  "scope": "read",
  "rate_limit_per_minute": 60
}
```

## Restrictions

API keys **cannot** access:

- API key management routes
- Platform admin routes (cache purge, plugin install, model seed)

## Storage

Only a SHA-256 hash and a short prefix are stored. The full key is shown once at creation.
