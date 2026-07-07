# ContentOS V5 — Mapa de consolidação

Epics V5 **estendem** módulos existentes sempre que possível.

## Epics por fase (detalhamento)


| Epic guarda-chuva           | Sub-IDs                | Ação        | Pacote / módulo base                                |
| --------------------------- | ---------------------- | ----------- | --------------------------------------------------- |
| **V5.0 Autonomia de mídia** | V5.0.1–V5.0.6          | misto       | `content-sources`, `media_analyze`, `intelligence/` |
| **V5.1 Voice Studio**       | V5.1.1, V5.1.2, V5.1.5 | **DONE**    | `voice` handler, `voice_profiles`, `/voice-studio`  |
| **V5.1 Cinematic Editor**   | V5.1.3                 | **ESTENDE** | `cinematic/`, `ffmpeg_filters`, `editor`            |
| **V5.1 DNA 2.0**            | V5.1.4                 | **ESTENDE** | `project_dna` V4 + `dna/pipeline_hints`             |
| **V5.2 Qualidade autônoma** | V5.2.1–V5.2.5          | misto       | `retention`, `multi_content`, KB + Learning         |
| **V5.3 Content Factory**    | V5.3.1–V5.3.5          | **DONE**    | `content_factory`, `/factory`, `content_batches`    |
| **V5.4 Pós-publicação**     | V5.4.1–V5.4.4          | **DONE**    | `learning`, OAuth analytics, community              |
| **V5.5 Enterprise**         | V5.5.1–V5.5.5          | **EVOLUI**  | `/executive`, KEDA, SLO                             |


## Itens implementados (referência rápida)


| ID     | Entrega                       | Status   |
| ------ | ----------------------------- | -------- |
| V5.0.1 | Pexels + Pixabay adapters     | **DONE** |
| V5.0.2 | `asset_collector` top-N       | **DONE** |
| V5.0.3 | Step `media_analyze`          | **DONE** |
| V5.0.4 | Take Recommendation           | **DONE** |
| V5.0.5 | Template `v5-media-autopilot` | **DONE** |
| V5.0.6 | Dashboard assets semântico    | **DONE** |
| V5.1.1 | Voice Profiles                | **DONE** |
| V5.1.2 | Voice Library por projeto     | **DONE** |
| V5.1.3 | Cinematic Editor v1           | **DONE** |
| V5.1.4 | Project DNA 2.0               | **DONE** |
| V5.1.5 | Dashboard `/voice-studio`     | **DONE** |
| V5.2.1 | Retention Engine              | **DONE** |
| V5.2.2 | Retention → auto_retry        | **DONE** |
| V5.2.3 | SEO Engine                    | **DONE** |
| V5.2.4 | AI Director v1                | **DONE** |
| V5.2.5 | Creative Memory               | **DONE** |
| V5.3.1 | BatchProductionService        | **DONE** |
| V5.3.2 | Variação hook/ângulo          | **DONE** |
| V5.3.3 | Quotas/custo por lote         | **DONE** |
| V5.3.4 | Dashboard `/factory`          | **DONE** |
| V5.3.5 | Aprovação antes de publicar   | **DONE** |
| V5.4.1 | OAuth Platform Analytics      | **DONE** |
| V5.4.2 | Performance Learning → KB     | **DONE** |
| V5.4.3 | Comment Analyzer              | **DONE** |
| V5.4.4 | Community Agent v1            | **DONE** |
| V5.5.1 | Command Center `/executive`   | **DONE** |
| V5.5.2 | Workers KEDA em produção      | **DONE** |
| V5.5.3 | SLO, alertas, runbooks        | **DONE** |
| V5.5.4 | Testes de carga + hardening   | **DONE** |
| V5.5.5 | PRODUCTION_READY + checklist  | **DONE** |


## Mapa técnico (módulos)


| Epic V5                              | Ação                          | Pacote / módulo base                                           |
| ------------------------------------ | ----------------------------- | -------------------------------------------------------------- |
| V5.0.1 Media Acquisition             | **ESTENDE**                   | `packages/content-sources/`                                    |
| V5.0.2 Collector top-N               | **ESTENDE**                   | `handlers/asset_collector.py`                                  |
| V5.0.3 Media Intelligence            | **NOVO** step `media_analyze` | `handlers/media_analyze.py` + `asset_media_profiles`           |
| V5.0.4 Take Recommendation           | **ESTENDE**                   | `intelligence/` + `asset_search` + `takes`                     |
| V5.0.5 Autopilot template            | **ESTENDE**                   | `workflow_templates.py`                                        |
| V5.0.6 Dashboard assets              | **ESTENDE**                   | `/assets` + busca semântica                                    |
| V5.1.1 Voice Profiles                | **ESTENDE**                   | `voice` handler + `voice_profiles` API                         |
| V5.1.2 Voice Library                 | **ESTENDE**                   | `voice_library` API + `/voice-library`                         |
| V5.1.3 Cinematic Editor              | **ESTENDE**                   | `cinematic/` + `ffmpeg_filters` + `editor`                     |
| V5.1.4 DNA 2.0                       | **ESTENDE**                   | `dna_v2`, `dna/pipeline_hints`, workflow inject                |
| V5.1 Voice Studio (guarda-chuva)     | **ESTENDE**                   | V5.1.1 + V5.1.2 + V5.1.5                                       |
| V5.1 Cinematic Editor (guarda-chuva) | **ESTENDE**                   | V5.1.3                                                         |
| V5.1 DNA 2.0 (guarda-chuva)          | **ESTENDE**                   | V5.1.4                                                         |
| V5.2.1 Retention Engine              | **NOVO**                      | agent `retention` + `RetentionAnalyzer` + `/retention`         |
| V5.2.2 Retention auto_retry          | **ESTENDE**                   | `retry_policy` + `auto_retry` + workflow engine                |
| V5.2.3 SEO Engine                    | **ESTENDE**                   | `seo` agent + `SeoOptimizer` + `/seo` + `publisher`            |
| V5.2.4 AI Director                   | **NOVO**                      | `ai_director` + `DirectorPlanner` + workflow engine            |
| V5.2.5 Creative Memory               | **MERGE**                     | `creative_memory` + Learning + KB + `/creative-memory`           |
| V5.3 Content Factory                 | **NOVO**                      | `content_factory` + `content_batches` + `/factory` + publisher hold |
| V5.4.1 OAuth Platform Analytics      | **NOVO**                      | `platform_analytics` + OAuth scopes + `/analytics/platforms`        |
| V5.4.2 Performance Learning          | **NOVO**                      | `performance_learning` + KB `performance` + `/learning`           |
| V5.4.3 Comment Analyzer              | **NOVO**                      | `comment_analyzer` + OAuth comments + `/learning`                 |
| V5.4.4 Community Agent               | **NOVO**                      | `community_agent` + `/community` (drafts only)                      |
| V5.4 Performance Learning            | **ESTENDE**                   | `learning` engine                                              |
| V5.4 Comment Analyzer                | **NOVO**                      | async agent pós-OAuth                                          |
| V5.5 Command Center                  | **EVOLUI**                    | `/executive` V5.5.1 Command Center                               |
| V5.5.2 KEDA workers                  | **ESTENDE**                   | `k8s/` pools v5-quality + v5-media + KEDA scalers              |
| V5.5.3 SLO / alertas / runbooks      | **NOVO**                      | `application/slo`, `/api/v1/ops`, Prometheus rules             |
| V5.5.4 Load test + hardening         | **NOVO**                      | `middleware/hardening`, `scripts/loadtest`, `/health/ready`     |
| V5.5.5 Production ready              | **NOVO**                      | `PRODUCTION_READY.md` — checklist go-live V5                   |


## Pipeline de mídia V5.0 (alvo)

```
scene → clip_research → asset_collector → asset_index
     → [media_analyze] → asset_search → takes → editor
```

Fontes licenciadas: `pexels`, `pixabay`, `own_library`, `local_library`, `custom`.

## DNA 2.0 → pipeline (V5.1.4)

O DNA do projeto injeta automaticamente no payload do workflow:

- `cinematic` — preset + overrides para o step `editor`
- `project_dna` / `content_angle` — ritmo e movement no `scene_director`
- `brand_keywords` — busca de assets e contexto de roteiro

