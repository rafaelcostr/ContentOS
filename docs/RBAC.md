# RBAC — Role-Based Access Control (Tier A5 + C2)

Roles exist at two levels:

1. **Platform** (`users.role`) — global admin for cache, plugins, model defaults.
2. **Organization** (`organization_members.role`) — scoped via `X-Organization-Id`.

When an org context is active, **membership role wins** over the global role.

Hierarchy: **admin > editor > viewer**

## Matrix (organization-scoped)

| Capability | viewer | editor | admin |
|------------|--------|--------|-------|
| Login / me | ✓ | ✓ | ✓ |
| List projects, pipelines, assets, videos | ✓ | ✓ | ✓ |
| Create project / pipeline | | ✓ | ✓ |
| Cancel / delete pipeline | | ✓ | ✓ |
| Upload / tag assets | | ✓ | ✓ |
| Update memory / prompts | | ✓ | ✓ |
| Add org members | | | ✓ |

## Platform-only (global `users.role = admin`)

| Capability | platform admin |
|------------|----------------|
| Cache purge | ✓ |
| Plugin install / enable | ✓ |
| Model seed / global model config | ✓ |

## Implementation

`apps/backend/src/contentos_gateway/api/deps.py`:

| Helper | Scope |
|--------|--------|
| `get_current_user` | Authenticated user |
| `get_org_auth_context` | User + org + effective role |
| `require_editor()` | Org editor+ (`X-Organization-Id`) |
| `require_org_admin` | Org admin (path `org_id`) |
| `require_platform_admin()` | Global platform admin |

`GET /api/v1/auth/me` returns `org_id` and `org_role` when org header is sent.

## Defaults

New registrations: global `editor` + **admin** on personal org.

Promote platform super-admin:

```sql
UPDATE users SET role = 'admin' WHERE email = 'you@example.com';
```

Change org role:

```sql
UPDATE organization_members SET role = 'viewer'
WHERE user_id = '...' AND organization_id = '...';
```

## API keys (Tier C5)

Public keys use `X-API-Key` instead of JWT. Scope maps to org role: `read` → viewer, `write` → editor. Keys cannot manage other keys or access platform admin routes. See [API_KEYS.md](./API_KEYS.md).

See also [MULTI_TENANT.md](./MULTI_TENANT.md).
