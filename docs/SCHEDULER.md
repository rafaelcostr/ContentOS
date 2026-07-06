# Scheduler (V3 Tier D1)

Cron-based automatic pipeline creation per project.

## Model

`pipeline_schedules` — linked to `project_id` and `org_id`:

| Field | Description |
|-------|-------------|
| `name` | Label in UI |
| `topic` | Pipeline topic (supports `{date}`, `{datetime}`) |
| `workflow_name` | Optional workflow template |
| `cron_expression` | Standard 5-field cron (e.g. `0 9 * * *`) |
| `timezone` | IANA timezone (default `UTC`) |
| `next_run_at` | Next trigger (UTC) |

## API

| Method | Path | Role |
|--------|------|------|
| `GET` | `/api/v1/projects/{project_id}/schedules` | member |
| `POST` | `/api/v1/projects/{project_id}/schedules` | editor+ |
| `PATCH` | `/api/v1/projects/{project_id}/schedules/{id}` | editor+ |
| `DELETE` | `/api/v1/projects/{project_id}/schedules/{id}` | editor+ |

### Create body

```json
{
  "name": "Daily video",
  "topic": "Trending topic {date}",
  "cron_expression": "0 9 * * *",
  "workflow_name": "v3-quality",
  "timezone": "America/Sao_Paulo"
}
```

## Runner

The gateway runs a background loop (default every **60s**) that:

1. Finds active schedules with `next_run_at <= now`
2. Calls workflow-engine `POST /internal/pipelines`
3. Updates `last_run_at`, `last_pipeline_id`, `next_run_at`
4. Stores `last_error` on quota/credit/network failures

Scheduled runs respect **quotas (C4)** and **credits (C3)** like manual pipelines.

## Configuration

```env
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_SECONDS=60
```

## Cron examples

| Expression | Meaning |
|------------|---------|
| `0 9 * * *` | Every day at 09:00 |
| `0 */6 * * *` | Every 6 hours |
| `30 8 * * 1` | Mondays at 08:30 |
