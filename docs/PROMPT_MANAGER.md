# Prompt Manager (ContentOS V2.2)

Versioned `.md` prompts with YAML frontmatter — edit without redeploying agents.

## Structure

```
packages/prompts/
├── prompts/           # bundled defaults (.md)
│   ├── research.md
│   ├── script.md
│   ├── scene.md
│   └── publisher.md
└── src/contentos_prompts/
    ├── application/prompt_service.py
    ├── infrastructure/loader.py
    └── infrastructure/registry.py
```

## Prompt format

```markdown
---
id: research
version: 1.0.0
agent: research
variables: [topic, memory_context, niche]
system: |
  You are a viral content researcher...
user: |
  Research viral angles for: {{topic}}
  Project style: {{memory_context}}
---
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/prompts` | List all prompts |
| GET | `/api/v1/prompts/{id}` | Get prompt detail + raw content |
| GET | `/api/v1/prompts/{id}/versions` | Version history |
| PUT | `/api/v1/prompts/{id}` | Hot reload (writes to override dir) |
| POST | `/api/v1/prompts/{id}/render` | Render with variables |
| POST | `/api/v1/prompts/reload` | Reload from disk |

All routes require JWT authentication.

## Agent integration

Handlers use `BaseAgentHandler.render_prompt()`:

```python
prompt = self.render_prompt("research", {"topic": topic, "memory_context": ""})
data = await ai.chat_json(prompt.system, prompt.user)
```

## Hot reload

Overrides are stored in `PROMPTS_OVERRIDE_DIR` (default `/data/prompts`), shared via Docker volume `prompts_data` between gateway and agents-worker.

After editing via API or dashboard, agents pick up changes on next job (service reloads from disk per `get_prompt_service()` cache — call `/prompts/reload` or restart worker to force refresh).

## Environment

```env
PROMPTS_DIR=/app/packages/prompts/prompts
PROMPTS_OVERRIDE_DIR=/data/prompts
```

## Dashboard

`/prompts` — list, edit, preview rendered output.
