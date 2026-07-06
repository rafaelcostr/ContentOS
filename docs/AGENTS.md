# ContentOS — Especificação dos Agentes

Todos os agentes implementam `BaseAgentHandler` e são invocados **exclusivamente** via fila Celery pelo Workflow Engine.

---

## 1. Research Agent

**Fila:** `contentos.research`

| Entrada | Saída |
|---------|-------|
| `topic: str` | `topics[]`, `selected_topic`, `summary` |

Fontes (via adapters): notícias, Reddit, Twitter/X, YouTube, fóruns. Usa OpenAI para ranking de viralidade.

---

## 2. Script Agent

**Fila:** `contentos.script`

| Entrada | Saída |
|---------|-------|
| `selected_topic` | `script` com hook, development, curiosity, cta, full_text |

Max 60 segundos de narração.

---

## 3. Scene Planner Agent

**Fila:** `contentos.scene`

| Entrada | Saída |
|---------|-------|
| `script` | `scenes[]` com start, end, description, visual_hint |

Exemplo: `{start: 0, end: 5, description: "Mostrar carro"}`

---

## 4. Takes Manager Agent

**Fila:** `contentos.takes`

| Entrada | Saída |
|---------|-------|
| `scenes[]` | `clips[]` com asset_ref por cena |

**Strategy Pattern:** `VideoSourceProvider` — v1 = biblioteca local MinIO; futuro = stock API, AI generation.

---

## 5. Voice Agent

**Fila:** `contentos.voice`

| Entrada | Saída |
|---------|-------|
| `script.full_text` | `audio` asset_ref (MP3) |

Provider: **ElevenLabs** (adapter substituível).

---

## 6. Subtitle Agent

**Fila:** `contentos.subtitle`

| Entrada | Saída |
|---------|-------|
| `audio` ref + `script` | `srt` ref + `captions.json` ref |

Engine: **Whisper** (OpenAI API).

---

## 7. Video Editor Agent

**Fila:** `contentos.editor`

| Entrada | Saída |
|---------|-------|
| clips, audio, captions | `render` asset_ref |

FFmpeg: 1080x1920, 60fps, H.264, zoom, transições, progress bar, SFX.

---

## 8. Quality Agent

**Fila:** `contentos.quality`

Validações técnicas com **nota 0–10** (`quality_score`):

| Dimensão | Critério |
|----------|----------|
| integrity | Render existe e não está corrompido |
| resolution | 1080×1920 |
| codec | H.264 |
| framerate | ~60fps |
| audio | Stream de áudio presente |
| duration | 15–60s ideal |
| subtitles | Segmentos ou arquivos de legenda |

Env: `QUALITY_MIN_SCORE=6` (default). Ver [QUALITY.md](./QUALITY.md).

Se falhar → Workflow reenvia **editor**. `video_review` usa o score técnico na dimensão **technical**.

---

## 9. Publisher Agent

**Fila:** `contentos.publisher`

| Entrada | Saída |
|---------|-------|
| render, script, topic | title, description, hashtags, thumbnail ref, status: ready |

v1: **não publica** automaticamente. Prepara artefatos para integração futura.
