# Quotas (V3 Tier C4)

Per-organization limits derived from the active **billing plan**.

## Limits

| Plan | Pipelines/month | Concurrent (workers) |
|------|-----------------|----------------------|
| `free` | 20 | 1 |
| `pro` | 500 | 5 |
| `enterprise` | ∞ (0) | ∞ (0) |

`0` means unlimited.

## Enforcement

Checked when creating a pipeline:

1. **Gateway** — `POST /api/v1/projects/{id}/pipelines`
2. **Workflow engine** — `POST /internal/pipelines` (defense in depth)

Exceeded quota returns **429** with body:

```json
{
  "detail": {
    "error": "quota_exceeded",
    "kind": "monthly_pipelines",
    "limit": 20,
    "current": 20
  }
}
```

Kinds: `monthly_pipelines`, `concurrent_pipelines`.

## Usage API

`GET /api/v1/organizations/{org_id}/billing` includes:

- `monthly_pipeline_quota` / `monthly_pipelines_used`
- `max_concurrent_pipelines` / `concurrent_pipelines_active`

## Configuration

```env
QUOTAS_ENFORCE=true
```

Set `QUOTAS_ENFORCE=false` to disable checks in local dev.

Monthly counts reset on the **1st UTC** (calendar month).

See also [BILLING.md](./BILLING.md).
