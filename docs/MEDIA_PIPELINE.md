# Media Pipeline — V5.0

Fluxo de aquisição de mídia licenciada para B-roll automático.

## Arquitetura

```
clip_research (por cena)
    → SourceManager.search_all_scenes()
    → adapters: pexels | pixabay | own_library | local_library | custom
asset_collector
    → SourceManager.fetch() → DownloadPipeline
    → AssetPipelineService (MinIO + PostgreSQL, SHA-256 dedup)
asset_index → media_analyze → asset_search → takes → editor
```

## Media Analyze (V5.0.3)

Após indexação, o agente `media_analyze`:

1. Extrai frames JPEG do vídeo (FFmpeg)
2. Analisa via AI Gateway `/v1/vision/analyze`
3. Gera embedding via `/v1/embeddings`
4. Persiste em `assets.metadata` + tabela `asset_media_profiles`

Tags automáticas: objetos, cenário, movimento, emoção, dia/noite, ângulo, tipo de câmera.

## Take Recommendation (V5.0.4)

Após `media_analyze`, o agente `asset_search` usa `TakeRecommendationService` para ranquear takes por cena:

| Sinal | Peso / comportamento |
|-------|----------------------|
| Scene label exato | +80 |
| Tag = label | +25 |
| Asset coletado na cena | +50 |
| Token overlap (tema, hint, objetos) | até +40 |
| Campos media_analyze (cenário, emoção, motion…) | +12 cada |
| Qualidade (tamanho, resolução) | até +20 |
| Fit de duração | até +10 |
| Fit de motion | +8 |
| Similaridade semântica (embeddings) | cosine × `TAKE_SCORE_SEMANTIC_WEIGHT` |
| Reuso do mesmo clip | −`TAKE_REUSE_PENALTY` |

API: `POST /api/v1/assets/recommend` com `{ "topic", "scenes" }`.

## V5 Media Autopilot (V5.0.5)

Template `v5-media-autopilot` — pipeline enxuto de 14 steps para produção autônoma de vídeo:

```
research → script → scene → clip_research → asset_collector → asset_index
        → media_analyze → asset_search → takes → voice → subtitle → editor → quality → publisher
```

Sem thumbnail/analytics — foco em tema → MP4 com B-roll licenciado.

```env
DEFAULT_WORKFLOW=v5-media-autopilot
E2E_WORKFLOW=v5-media-autopilot
E2E_TOPIC=GTA 6
```

E2E local:

```bash
python scripts/e2e_pipeline.py
```

Testes unitários GTA 6:

```bash
pytest tests/test_v5_media_autopilot.py -q
```

## Dashboard — busca semântica (V5.0.6)

O dashboard `/assets` ganhou modo **Semântica (IA)**:

- Consulta em linguagem natural (ex.: `praia GTA 6 ao pôr do sol`)
- Ranking por cosine similarity nos embeddings de `asset_media_profiles`
- Fallback por overlap de texto quando não há embedding
- Exibe score %, tipo de match (`embedding` | `text`) e análise de mídia no painel de detalhe

API: `GET /api/v1/assets/search/semantic?q=...&category=takes&limit=50`

```env
ENABLE_ASSET_SEMANTIC_SEARCH=true
ASSET_SEMANTIC_MIN_SIMILARITY=0.12
ASSET_SEMANTIC_CANDIDATE_LIMIT=500
```

```bash
pytest tests/test_asset_semantic_search.py -q
```

## Adapters licenciados (V5.0.1)

| ID | API | Licença |
|----|-----|---------|
| `pexels` | https://www.pexels.com/api/ | Pexels License (royalty_free) |
| `pixabay` | https://pixabay.com/api/docs/ | Pixabay License (royalty_free) |

## Environment

```env
ENABLE_V2_CLIP_PIPELINE=true
CONTENT_SOURCES_ENABLED=pexels,pixabay,own_library,local_library
PEXELS_API_KEY=
PIXABAY_API_KEY=
MEDIA_MAX_DOWNLOAD_MB=50
MEDIA_ALLOWED_LICENSES=royalty_free,creative_commons
MEDIA_COLLECT_TOP_N=3
MEDIA_SEARCH_PER_PAGE=8
ENABLE_MEDIA_ANALYZE=true
MEDIA_ANALYZE_MAX_FRAMES=2
ENABLE_TAKE_RECOMMENDATION=true
TAKE_SCORE_SEMANTIC_WEIGHT=40
TAKE_REUSE_PENALTY=25
```

## Componentes

| Classe | Path |
|--------|------|
| `DownloadPipeline` | `content-sources/application/download_pipeline.py` |
| `MediaAnalyzeService` | `storage/application/media_analyze_service.py` |
| `media_analyze` handler | `agents-worker/handlers/media_analyze.py` |
| `TakeRecommendationService` | `intelligence/application/take_recommendation/service.py` |
| `AssetSemanticSearch` | `intelligence/application/asset_semantic_search.py` |
| `asset_search` handler | `agents-worker/handlers/asset_search.py` |
| `PexelsSource` | `content-sources/adapters/pexels.py` |
| `PixabaySource` | `content-sources/adapters/pixabay.py` |

## Política

- Apenas fontes com licença documentada em `metadata.license_type`.
- `MEDIA_ALLOWED_LICENSES` bloqueia fetch de licenças não permitidas.
- Sem scrape de redes sociais (TikTok, Instagram, etc.).

## Tests

```bash
pytest tests/test_media_acquisition.py tests/test_media_analyze.py tests/test_take_recommendation.py tests/test_asset_search.py -q
```

## ADR

[ADR-009](./ADR.md#adr-009--aquisição-de-mídia-licenciada-v50)
