# Multi Content — Epic 2a (V4.2.1)

Um roteiro de vídeo → **5 artefatos de texto** reutilizáveis.

## Formatos (piloto texto)

| Formato | Prompt | Uso |
|---------|--------|-----|
| `thread_x` | `thread_x.md` | Thread X/Twitter |
| `linkedin_post` | `linkedin_post.md` | Post LinkedIn |
| `newsletter` | `newsletter.md` | Newsletter email |
| `seo_article` | `seo_article.md` | Artigo SEO |
| `email_marketing` | `email_marketing.md` | Email marketing |

## Workflow

Template **`v4-multi-text`** (18 steps) = `v4-intelligence` + `multi_content` após `publisher`.

```
… → publisher → multi_content
```

`v4-intelligence` permanece inalterado (17 steps).

## Handler

`MultiContentAgentHandler` (`step=multi_content`):

1. Lê `script.full_text` do payload
2. Gera cada formato via LLM (prompts) com fallback heurístico
3. Persiste em `multi_content_artifacts` + asset `multi_content.json`
4. Emite `multi_content.generated`

## Payload

```json
{
  "multi_content_report": {
    "artifact_count": 5,
    "artifacts": [
      { "format": "thread_x", "title": "...", "content": "...", "source": "llm" }
    ],
    "by_format": { "thread_x": { "...": "..." } }
  }
}
```

## API

| Method | Path |
|--------|------|
| `POST` | `/api/v1/multi-content/generate` |
| `GET` | `/api/v1/multi-content/pipeline/{pipeline_id}` |

## Integração Content Score

Dimensão **SEO** usa `seo_article` do `multi_content_report` quando disponível.

## Environment

| Variable | Default |
|----------|---------|
| `MULTI_CONTENT_ENABLED` | `true` |
| `MULTI_CONTENT_USE_LLM` | `true` |
| `MULTI_CONTENT_FORMATS` | todos os 5 formatos |

## Dashboard

`/multi-content` — gerar e visualizar artefatos.

## Tests

```bash
pytest tests/test_multi_content.py -q
```

## Migration

`013_v4_multi_content.py` — tabela `multi_content_artifacts`

---

# Multi Content Video — Epic 2b (V4.2.2)

Um render de vídeo → **3 variantes de plataforma** com metadata e crop specs.

## Plataformas (piloto vídeo)

| Plataforma | Prompt | Crop |
|------------|--------|------|
| `tiktok` | `tiktok_metadata.md` | 1080×1920, max 180s |
| `youtube_shorts` | `youtube_shorts_metadata.md` | 1080×1920, max 60s |
| `instagram_reels` | `instagram_reels_metadata.md` | 1080×1920, max 90s |

## Workflow

Template **`v4-multi-full`** (19 steps) = `v4-multi-text` + `multi_content_video` após `multi_content`.

```
… → publisher → multi_content → multi_content_video
```

`v4-multi-text` permanece inalterado (18 steps).

## Handler

`MultiContentVideoAgentHandler` (`step=multi_content_video`):

1. Lê `publication`, `script` e `render_ref` do payload
2. Gera metadata por plataforma via LLM (prompts) com fallback heurístico
3. Persiste em `video_platform_variants` + atualiza `Video.platform_variants`
4. Emite `video_variants.generated`

## Payload

```json
{
  "video_variants_report": {
    "variant_count": 3,
    "variants": [
      {
        "platform": "tiktok",
        "title": "...",
        "description": "...",
        "hashtags": ["viral"],
        "crop_spec": { "width": 1080, "height": 1920, "max_duration_seconds": 180 },
        "render_ref": { "id": "..." },
        "metadata": { "ready_to_publish": true }
      }
    ],
    "by_platform": { "tiktok": { "...": "..." } }
  }
}
```

## API (vídeo)

| Method | Path |
|--------|------|
| `POST` | `/api/v1/multi-content/video-variants/generate` |
| `GET` | `/api/v1/multi-content/video-variants/pipeline/{pipeline_id}` |

## Environment (vídeo)

| Variable | Default |
|----------|---------|
| `MULTI_CONTENT_VIDEO_ENABLED` | `true` |
| `MULTI_CONTENT_VIDEO_USE_LLM` | `true` |
| `MULTI_CONTENT_VIDEO_PLATFORMS` | `tiktok,youtube_shorts,instagram_reels` |

## Tests (vídeo)

```bash
pytest tests/test_multi_content_video.py -q
```

## Migration (vídeo)

`014_v4_video_platform_variants.py` — tabela `video_platform_variants` + coluna `videos.platform_variants`
