# Cache Manager (ContentOS V2.5)

Redis cache for LLM JSON responses — avoids repeated AI calls for the same topic.

## Cache key

```
SHA256(agent + topic + prompt_version + model + memory_context)[:32]
→ contentos:cache:{agent}:{hash}
```

## TTL per agent

| Agent | TTL |
|-------|-----|
| research | 7 days |
| script, scene, publisher | 1 day |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/cache/stats` | Total keys + breakdown by agent |
| DELETE | `/api/v1/cache/agent/{agent}` | Purge all keys for agent |
| DELETE | `/api/v1/cache/{key}` | Delete single key (full Redis key) |

## Environment

```env
USE_AI_CACHE=true
CACHE_REDIS_URL=redis://redis:6379/2
CACHE_DEFAULT_TTL_SECONDS=86400
```

Uses Redis DB **2** by default (Celery uses 0/1).

## Integration

`BaseAgentHandler.chat_json_with_cache()` wraps text LLM calls in research, script, scene, and publisher agents.

Logs show `Cache hit (contentos:cache:...)` when served from cache.

## Dashboard

`/cache` — stats, TTL table, purge per agent.
