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

### Campos DNA 2.0 (V5.1.4)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `cinematic_preset` | `default` \| `dynamic` \| `calm` \| `punchy` | Preset do editor cinematográfico |
| `content_angle` | `hype` \| `documentary` \| `tutorial` \| … | Ângulo criativo → scene_director |
| `brand_keywords` | list | Palavras-chave para busca de assets e roteiro |
| `editing_preferences` | json | Overrides opcionais (zoom, ducking, music_volume) |
| `default_voice_builtin` | string | Voz built-in padrão do projeto (V5.1.2) |

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
  "cta_style": "urgente",
  "cinematic_preset": "dynamic",
  "content_angle": "hype",
  "brand_keywords": ["GTA", "open world"],
  "editing_preferences": {"music_volume": 0.14}
}
```

## Injeção automática no pipeline (V5.1.4)

O Workflow Engine injeta no payload (quando não definido explicitamente):

| Chave | Steps afetados |
|-------|----------------|
| `cinematic` | `editor` |
| `content_angle` / `project_dna` | `scene_director` |
| `brand_keywords` | `asset_search`, roteiro |
| `voice_profile_name` | `voice` (V5.1.2) |

Módulo: `contentos_shared/dna/pipeline_hints.py`

## Migration

`010_v4_project_dna` — colunas V4.  
`021_v5_dna_v2` — colunas DNA 2.0 (`cinematic_preset`, `content_angle`, `brand_keywords`, `editing_preferences`).

```bash
cd packages/database && alembic upgrade head
```

## Roadmap

Parte da Fase V4.0 — base para Specialists (Epic 5) e Viral Intelligence (Epic 1).
