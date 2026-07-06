# Workflow Builder (V3 Tier D2)

Visual builder for **custom organization workflows** stored as `WorkflowDefinition` rows.

## Features

- Drag-and-drop step ordering (HTML5 DnD in dashboard)
- Org-scoped custom workflows (`org_id` + `slug`)
- Built-in templates remain read-only (`is_builtin=true`)
- Engine loads custom workflows by `name` (`org-{uuid}-{slug}`)

## API

| Method | Path | Role |
|--------|------|------|
| `GET` | `/api/v1/workflows/steps/catalog` | member |
| `GET` | `/api/v1/workflows` | member (builtins + org custom) |
| `GET` | `/api/v1/workflows/{name}` | member |
| `POST` | `/api/v1/workflows/custom` | editor+ |
| `PUT` | `/api/v1/workflows/custom/{slug}` | editor+ |
| `DELETE` | `/api/v1/workflows/custom/{slug}` | editor+ |

### Create body

```json
{
  "slug": "quality-lite",
  "description": "Short V3 path",
  "steps": ["research", "hook", "script", "editor", "publisher"]
}
```

Stored `name`: `org-{organization_id}-quality-lite`

Use that `name` (or resolve via slug in UI) when starting pipelines or schedules.

## Dashboard

**Produção → Workflow Builder** (`/workflows/builder`)

## Validation

- Slug: lowercase, hyphens, 1–50 chars, no builtin name collision
- Steps: known `PipelineStep` values only, no duplicates, min 1

## Migration

`009_d2_workflow_builder.py` adds `slug`, `org_id`, `is_builtin`, `created_by_user_id` to `workflows`.
