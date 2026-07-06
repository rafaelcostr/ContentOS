# Multi-tenant (Tier C1)

ContentOS isolates data by **Organization**. Users belong to one or more orgs via **OrganizationMember**.

## Model

| Table | Purpose |
|-------|---------|
| `organizations` | Tenant workspace (`name`, `slug`, `is_personal`) |
| `organization_members` | User ↔ org with role (`admin`, `editor`, `viewer`) |
| `projects.org_id` | Project belongs to an org |
| `pipelines.org_id` | Denormalized from project for filtered listing |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/organizations` | List orgs for current user |
| POST | `/api/v1/organizations` | Create team org (caller = admin) |
| GET | `/api/v1/organizations/{id}` | Org detail |
| GET | `/api/v1/organizations/{id}/members` | List members |
| POST | `/api/v1/organizations/{id}/members` | Add member (org admin) |

## Context header

Send active org on project/pipeline list requests:

```
X-Organization-Id: <uuid>
```

If omitted, the user's first org (personal workspace first) is used.

## Bootstrap

- **Register**: creates a personal org + admin membership.
- **Startup**: `backfill_organizations()` assigns orgs to legacy users/projects.
- **Migration**: `alembic upgrade head` (revision `004_c1_organizations`).

## Dashboard

Sidebar **Organização** selector stores `contentos_org_id` in `localStorage` and sends the header on all API calls.

## RBAC (C2)

Mutations (`require_editor`) check **organization membership role** via `X-Organization-Id`. A global `editor` who is `viewer` in an org cannot create pipelines there.

Platform operations (cache, plugins, model defaults) require **platform admin** (`users.role = admin`).

`GET /auth/me` returns `org_role` when org header is present.
