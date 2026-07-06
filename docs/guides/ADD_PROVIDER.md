# Como adicionar um AI Provider

## Visão

```
Agente → Gateway*Provider (ai-client) → AI Gateway → ProviderRegistry → Adapter
```

Com `USE_AI_GATEWAY=true` (padrão), agentes **nunca** importam SDKs de terceiros diretamente.

## Passos

### 1. Implementar adapter

Crie em `packages/ai-core/src/contentos_ai/infrastructure/adapters/{text|speech|subtitle|image|vision|embedding}/`:

```python
class MeuTextAdapter:
    name = "meu_provider"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or "default-model"

    async def chat_json(self, system: str, user: str) -> dict:
        ...
```

Protocolos em `packages/ai-core/src/contentos_ai/domain/protocols.py`:

- `TextProvider` — `chat_json`
- `SpeechProvider` — `text_to_speech`
- `SubtitleProvider` — `transcribe`
- `ImageProvider` — `generate_image`
- `VisionProvider` — `analyze_image`
- `EmbeddingProvider` — `embed`

### 2. Registrar no ProviderRegistry

Em `packages/ai-core/src/contentos_ai/domain/registry.py`, adicione o caminho pontilhado:

```python
TEXT_REGISTRY: dict[str, str] = {
    ...
    "meu_provider": "contentos_ai.infrastructure.adapters.text.meu.MeuTextAdapter",
}
```

O `ProviderRegistry` (`application/provider_registry.py`) carrega essas entradas automaticamente.

Registro dinâmico (runtime):

```python
from contentos_ai import get_provider_registry

get_provider_registry().register("text", "meu_provider", "contentos_ai....MeuTextAdapter")
```

### 3. Expor via AI Gateway

O serviço `services/ai-gateway` usa `AIService` + registry. Verifique:

```powershell
curl http://localhost:8020/health
curl http://localhost:8020/v1/providers
curl "http://localhost:8020/v1/providers/resolve?agent=script&provider_type=text"
```

### 4. Configurar ambiente / Model Manager

```env
TEXT_PROVIDER=meu_provider
# ou por agente no dashboard /models (tabela agent_model_configs)
```

### 5. Fallback local (opcional)

Se `AI_GATEWAY_FALLBACK=true` e o gateway cair, o `ai-client` usa adapters diretos em `packages/shared/providers/` (apenas ollama/openai/piper/whisper locais). Para cloud providers, mantenha o gateway disponível.

### 6. Testar

```powershell
pytest tests/test_ai_gateway.py tests/test_ai_gateway_routing.py tests/test_advanced_providers.py -v
```

## Checklist

- [ ] Adapter implementa protocolo do domínio
- [ ] Entrada em `domain/registry.py`
- [ ] Variáveis em `.env.example`
- [ ] Aparece em `GET /v1/providers`
- [ ] Teste unitário do adapter
