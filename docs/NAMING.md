# Naming — Missão vs Código

A missão descreve módulos com nomes conceituais. O código usa nomes equivalentes (às vezes mais específicos). Este mapa evita confusão ao estender o sistema.

| Missão | Código | Pacote / caminho |
|--------|--------|------------------|
| AI Gateway | `AIService` + FastAPI app | `services/ai-gateway`, `packages/ai-core` |
| ProviderRegistry | `ProviderRegistry` | `packages/ai-core/.../provider_registry.py` |
| ProviderFactory | `AIProviderFactory` / `ProviderFactory` | `ai-core` / `shared/providers/factory.py` |
| PromptLoader | `PromptLoader` | `packages/prompts` |
| PromptRegistry | `PromptRegistry` | `packages/prompts` |
| PromptVersion | `PromptVersion` | `packages/prompts` |
| PromptEditor | `PromptService.update_prompt` + UI `/prompts` | sem classe `PromptEditor` |
| Model Manager | `ModelManager` | `packages/models` |
| Memory Manager | `MemoryService` | `packages/memory` |
| Event Bus | `EventBusPublisher` / domain events | `packages/events` |
| Cache Manager | `CacheService` | `packages/cache` |
| Cost Manager | `CostTracker` | `packages/cost` |
| Analytics AI | `AnalyticsService` + handler | `packages/analytics-ai` |
| Plugin Marketplace | `PluginMarketplace` | `packages/plugins-core` |
| ContentSource | `ContentSource` (Protocol) | `packages/content-sources` |
| SourceFactory | `build_registry()` | `content-sources/.../factory.py` |
| SourceRegistry | `SourceRegistry` | `content-sources/.../registry.py` |
| ContentSourceManager | `SourceManager` | `content-sources/.../source_manager.py` |
| Clip Research Agent | `ClipResearchAgentHandler` | `handlers/clip_research.py` |
| Asset Collector | `AssetCollectorAgentHandler` | `handlers/asset_collector.py` |
| Asset Manager V2 | `AssetManager` + `AssetPipelineService` + `AssetIndexService` | `packages/storage` |
| Takes Manager | `TakesAgentHandler` | `handlers/takes.py` |
| StorageProvider | `AssetManager` (MinIO) | nunca acessar MinIO direto nos agentes |

## Providers de IA

| Protocolo | Registry key type | Adapters padrão |
|-----------|-------------------|-----------------|
| TextProvider | `text` | ollama, openai, claude, … |
| SpeechProvider | `speech` | piper, elevenlabs |
| SubtitleProvider | `subtitle` | local/whisper, openai |
| ImageProvider | `image` | local (Pillow) |
| VisionProvider | `vision` | ollama (llava) |
| EmbeddingProvider | `embedding` | ollama |

## Workflow templates

| Nome env / API | Steps |
|----------------|-------|
| `v1-default` | 9 |
| `v2-full` | 9 + agents async |
| `v2-dynamic` | 16 (missão completa + media_analyze) |

