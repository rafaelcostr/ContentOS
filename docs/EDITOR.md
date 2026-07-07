# ContentOS — Editor Agent (Fase 3)

## Responsabilidade

Montar o vídeo final **1080x1920 @ 60fps H264** a partir de:

- Cenas (timeline do Scene Planner)
- Takes (clips do Asset Manager)
- Narração (Voice Agent)
- Legendas SRT (Subtitle Agent)

---

## Efeitos FFmpeg

| Efeito | Implementação |
|--------|---------------|
| **Zoom (Ken Burns)** | `zoompan` — zoom suave 1.0 → 1.12 por cena |
| **Fade in/out** | `fade=t=in/out` — 0.4s por cena |
| **Transições** | Concatenação de segmentos processados |
| **Legendas** | Burn-in SRT com estilo bold + outline |
| **Barra de progresso** | `drawbox` animado na base do vídeo |
| **Música de fundo** | Ambient gerado (lavfi) ou `assets/music/ambient.mp3` no MinIO |
| **Speed ramp** | `setpts` linear por cena (0.5×–2.0×) |
| **Ducking** | `sidechaincompress` — música abaixa quando há narração |
| **Presets** | `default`, `dynamic`, `calm`, `punchy` via payload ou env |
| **Mix de áudio** | Narração loudnorm + música com ducking real ou `amix` simples |

---

## Cinematic Editor v1 (V5.1.3)

Payload opcional no step `editor`:

```json
{
  "cinematic": {
    "preset": "dynamic",
    "enable_zoom": true,
    "enable_ducking": true,
    "enable_speed_ramp": true,
    "music_volume": 0.14,
    "ducking_ratio": 10,
    "ducking_threshold": 0.025
  }
}
```

Movements no storyboard / director plan: `speed-ramp-up`, `speed-ramp-down`, `slow-mo`.

Módulo: `contentos_shared/cinematic/` — `CinematicSettings`, presets, `apply_directive_to_segment`.

---

## Configuração (.env)

```env
ENABLE_CINEMATIC_EDITOR=true
CINEMATIC_PRESET=default
EDITOR_ENABLE_ZOOM=true
EDITOR_MUSIC_VOLUME=0.12
EDITOR_MUSIC_KEY=assets/music/ambient.mp3
EDITOR_FADE_DURATION=0.4
```

Upload música customizada:

```bash
# Via dashboard Storage ou API assets
PUT takes/... → assets/music/ambient.mp3
```

---

## Quality Agent

Valida antes de publicar:

| Check | Regra |
|-------|-------|
| Resolução | 1080x1920 |
| Codec | H264 |
| FPS | ≥ 55 |
| Duração | ≤ 60s |
| Áudio | Stream presente |
| Legendas | Segments no payload |
| Corrupção | Tamanho mínimo 10KB |

Falha → retry automático no **Editor** via Workflow Engine.

---

## Arquitetura

```
EditorAgentHandler
    ↓
RenderSpec + SceneSegment[] (ffmpeg_filters.py)
    ↓
FFmpegProvider.render_timeline()
    ↓
MinIO renders/final.mp4
    ↓
QualityAgentHandler (probe + validate)
    ↓
PublisherAgentHandler
```

Filtros puros em `ffmpeg_filters.py` — testáveis sem executar FFmpeg.

---

## Dashboard

`/jobs` — pipeline visual em tempo real:

- Lista pipelines recentes
- 9 steps com status (pending/running/completed/failed)
- WebSocket + polling 3s
- Barra de progresso %

API: `GET /api/v1/pipelines`, `GET /api/v1/pipelines/{id}`
