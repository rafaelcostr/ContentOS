# Project DNA (ContentOS V4 — Epic 8)

Identidade criativa por projeto, estendendo `ProjectMemory` sem tabela paralela.

## Campos DNA

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `humor_level` | float 0–1 | Intensidade de humor |
| `pace` | `slow` \| `medium` \| `fast` | Velocidade do conteúdo |
| `visual_style` | json | Cores, tipografia, mood |
| `narrator_persona` | string | Persona/voz do narrador |
| `preferred_formats` | list | tiktok, youtube_shorts, article, … |
| `hook_patterns` | list | Padrões de abertura favoritos |
| `cta_style` | string | urgente, suave, pergunta, … |

Campos V3 (`tone`, `vocabulary`, `niche`, …) permanecem na mesma linha `project_memory`.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/projects/{id}/dna` | DNA do projeto + preview |
| PATCH | `/api/v1/projects/{id}/dna` | Atualização parcial (só campos enviados) |
| GET | `/api/v1/projects/{id}/memory` | Memória completa (inclui DNA) |
| PUT | `/api/v1/projects/{id}/memory` | Atualização completa da memória |

## Injeção automática em prompts

`BaseAgentHandler.render_prompt(..., project_id=...)` preenche:

| Variável | Conteúdo |
|----------|----------|
| `memory_context` | Memória V3 + DNA |
| `dna_context` | Somente bloco DNA |
| `niche` | Nicho do projeto |
| `narrator_persona` | Persona narrador |
| `pace` | Ritmo |
| `cta_style` | Estilo de CTA |

## Exemplo PATCH

```json
PATCH /api/v1/projects/{id}/dna
{
  "humor_level": 0.7,
  "pace": "fast",
  "narrator_persona": "hype gamer",
  "preferred_formats": ["tiktok", "youtube_shorts"],
  "visual_style": {"primary_color": "#FF0050", "mood": "neon"},
  "hook_patterns": ["pergunta chocante", "número nos 3s"],
  "cta_style": "urgente"
}
```

## Migration

`010_v4_project_dna` — colunas aditivas em `project_memory`.

```bash
cd packages/database && alembic upgrade head
```

## Roadmap

Parte da Fase V4.0 — base para Specialists (Epic 5) e Viral Intelligence (Epic 1).
