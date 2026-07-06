# Como adicionar uma Content Source

## Visão

```
Clip Research → SourceManager → ContentSource adapters → candidatos por cena
Asset Collector → fetch() → AssetPipelineService (MinIO + PostgreSQL)
```

**Naming:** na missão, `ContentSourceManager` = código `SourceManager`.  
`SourceFactory` = função `build_registry()` em `infrastructure/factory.py`.

## Passos

### 1. Implementar adapter

Crie em `packages/content-sources/src/contentos_sources/infrastructure/adapters/` (ou pasta de adapters do pacote):

```python
from contentos_sources.domain.content_source import ContentSource

class MinhaSource:
    source_id = "minha_source"

    async def search(self, query: str, project_id, limit: int = 5) -> list:
        ...

    async def fetch(self, candidate_id: str):
        ...
```

### 2. Registrar

Em `packages/content-sources/src/contentos_sources/infrastructure/factory.py` (`build_registry`), registre a source no `SourceRegistry`.

O `SourceManager` (`application/source_manager.py`) consulta o registry.

### 3. Habilitar via env

```env
CONTENT_SOURCES_ENABLED=local_library,own_library,minha_source
```

### 4. Dashboard

Página `/content-sources`. API:

```http
GET /api/v1/content-sources
GET /api/v1/content-sources/health
```

### 5. Pipeline

- **`v2-full`**: clip research async após `scene`
- **`v2-dynamic`**: steps `clip_research` → `asset_collector` → `asset_index`

O **Asset Collector** persiste assets via `AssetPipelineService` (hash dedup global).

### 6. Testar

```powershell
pytest tests/test_content_sources.py tests/test_asset_pipeline.py -v
```

## Checklist

- [ ] Implementa protocolo `ContentSource`
- [ ] Registrado em `build_registry` / `SourceRegistry`
- [ ] Em `CONTENT_SOURCES_ENABLED`
- [ ] `fetch` retorna mídia (não só JSON de referência, se for para o collector)
- [ ] Teste unitário
