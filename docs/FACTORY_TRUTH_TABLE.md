# Factory Truth Table

Tabela única da linha de montagem `factory-full` (31 steps executáveis).

Fontes de verdade:

- Ordem: `PipelineStep.factory_full_ordered()`
- Mapa produto: `factory_map.py`
- Contrato: `tests/test_factory_full_contract.py` + `tests/test_factory_truth_table.py`

Regenerar:

```bash
python scripts/generate_factory_truth_table.py
```

| # | Step | Módulo | Status | Handler | Fila | Evento | Dependência externa |
|---:|---|---|---|---|---|---|---|
| 1 | `research` | creative | ready | `contentos_agents.handlers.research` | `contentos.research` | `research.finished` | ollama |
| 2 | `trend_intelligence` | intelligence | ready | `contentos_agents.handlers.trend_intelligence` | `contentos.trend_intelligence` | `trend_intelligence.finished` | rules+postgres |
| 3 | `hook` | creative | ready | `contentos_agents.handlers.hook` | `contentos.hook` | `hook.finished` | ollama |
| 4 | `script` | creative | ready | `contentos_agents.handlers.script` | `contentos.script` | `script.finished` | ollama |
| 5 | `script_review` | creative | ready | `contentos_agents.handlers.script_review` | `contentos.script_review` | `script_review.finished` | ollama |
| 6 | `scene` | creative | ready | `contentos_agents.handlers.scene` | `contentos.scene` | `scene.created` | ollama |
| 7 | `storyboard` | creative | ready | `contentos_agents.handlers.storyboard` | `contentos.storyboard` | `storyboard.finished` | ollama |
| 8 | `scene_director` | creative | ready | `contentos_agents.handlers.scene_director` | `contentos.scene_director` | `scene_director.finished` | rules |
| 9 | `clip_research` | assets | partial | `contentos_agents.handlers.clip_research` | `contentos.clip_research` | `clip_research.finished` | content-sources |
| 10 | `asset_collector` | assets | partial | `contentos_agents.handlers.asset_collector` | `contentos.asset_collector` | `assets.ready` | content-sources+minio |
| 11 | `asset_index` | assets | ready | `contentos_agents.handlers.asset_index` | `contentos.asset_index` | `asset_index.finished` | postgres+minio |
| 12 | `media_analyze` | assets | ready | `contentos_agents.handlers.media_analyze` | `contentos.media_analyze` | `media_analyze.finished` | ollama+minio |
| 13 | `asset_search` | assets | ready | `contentos_agents.handlers.asset_search` | `contentos.asset_search` | `asset_search.finished` | postgres |
| 14 | `takes` | assets | ready | `contentos_agents.handlers.takes` | `contentos.takes` | `takes.finished` | minio |
| 15 | `voice` | production | ready | `contentos_agents.handlers.voice` | `contentos.voice` | `voice.generated` | piper |
| 16 | `subtitle` | production | ready | `contentos_agents.handlers.subtitle` | `contentos.subtitle` | `subtitle.created` | whisper |
| 17 | `editor` | production | ready | `contentos_agents.handlers.editor` | `contentos.editor` | `editor.finished` | ffmpeg+minio |
| 18 | `thumbnail` | production | partial | `contentos_agents.handlers.thumbnail` | `contentos.thumbnail` | `thumbnail.created` | ollama+image |
| 19 | `quality` | quality | ready | `contentos_agents.handlers.quality` | `contentos.quality` | `quality.approved` | ffprobe |
| 20 | `retention` | quality | ready | `contentos_agents.handlers.retention` | `contentos.retention` | `retention.analyzed` | rules+ffprobe |
| 21 | `video_review` | quality | ready | `contentos_agents.handlers.video_review` | `contentos.video_review` | `video_review.finished` | ollama |
| 22 | `auto_retry` | quality | ready | `contentos_agents.handlers.auto_retry` | `contentos.auto_retry` | `auto_retry.finished` | rules+workflow-engine |
| 23 | `content_score` | quality | ready | `contentos_agents.handlers.content_score` | `contentos.content_score` | `content_score.computed` | rules |
| 24 | `ai_director` | quality | ready | `contentos_agents.handlers.ai_director` | `contentos.ai_director` | `director.decided` | rules |
| 25 | `content_intelligence` | intelligence | ready | `contentos_agents.handlers.content_intelligence` | `contentos.content_intelligence` | `content_intelligence.finished` | rules |
| 26 | `learning` | intelligence | ready | `contentos_agents.handlers.learning` | `contentos.learning` | `learning.recorded` | rules+postgres |
| 27 | `knowledge_base` | intelligence | ready | `contentos_agents.handlers.knowledge_base` | `contentos.knowledge_base` | `knowledge_base.indexed` | postgres |
| 28 | `creative_memory` | intelligence | ready | `contentos_agents.handlers.creative_memory` | `contentos.creative_memory` | `creative_memory.merged` | rules+postgres |
| 29 | `analytics` | intelligence | ready | `contentos_agents.handlers.analytics` | `contentos.analytics` | `analytics.processed` | ollama+postgres |
| 30 | `seo` | publishing | ready | `contentos_agents.handlers.seo` | `contentos.seo` | `seo.optimized` | ollama |
| 31 | `publisher` | publishing | partial | `contentos_agents.handlers.publisher` | `contentos.publisher` | `publisher.finished` | ollama+oauth-plugins |
