# Specialist Agents — Epic 5 (V4.1.3)

Automatic niche specialist selection and prompt injection — **same workers**, different persona.

## Pilot specialists (3 of 11)

| ID | Nicho | Prompt pack |
|----|-------|-------------|
| `gaming` | Jogos / esports | `gaming_v1` |
| `technology` | Tech / IA / software | `technology_v1` |
| `business` | Negócios / marketing | `business_v1` |
| `general` | Fallback | `general_v1` |

8 nichos adicionais estão catalogados como `coming_soon` (fase futura).

## Architecture

```
content_intelligence
├── specialist_selector   (Epic 5) — primeiro no step
├── reuse_advisor
├── viral_engine
├── ab_testing
└── content_score
```

**Não há** workers separados por nicho. O `BaseAgentHandler.render_prompt` injeta `specialist_context` no `memory_context` para todos os agentes downstream (scene, storyboard, publisher, etc.).

## Selection signals

- `project_memory.niche` / payload `niche`
- Tópico e título do script
- Keywords por nicho (gaming, technology, business)
- Override: `payload.specialist_id`

## Payload output

```json
{
  "specialist_selection": {
    "specialist": { "specialist_id": "gaming", "name": "Gaming Specialist", "...": "..." },
    "confidence": 0.82,
    "reason": "niche_hint=gaming, keyword:gta"
  },
  "specialist_id": "gaming",
  "specialist_context": "Especialista: Gaming Specialist (nicho gaming). Tom: ...",
  "specialist_prompt_pack": "gaming_v1",
  "niche": "gaming"
}
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/specialists` | Lista pilot + opcional `?include_upcoming=true` |
| `GET` | `/api/v1/specialists/{id}` | Detalhe |
| `POST` | `/api/v1/specialists/select` | Seleção manual por tópico |

## Events

- `specialist.selected` (alias `SpecialistSelected`)

## Agent catalog

`agent_catalog.py` ganhou `specialist_suites` nos agentes criativos (`hook`, `script`, `scene`).

## Environment

| Variable | Default |
|----------|---------|
| `SPECIALIST_SELECTION_ENABLED` | `true` |

## Dashboard

`/specialists` — listar e testar seleção por tópico.

## Tests

```bash
pytest tests/test_specialists.py -q
```
