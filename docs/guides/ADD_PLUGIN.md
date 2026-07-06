# Como adicionar um Plugin

## Visão

```
Publisher Agent → PluginLoader → PlatformPlugin → publish() / hooks
```

Plugins vivem em `plugins/marketplace/` (built-in) ou `plugins/installed/` (pós-install).

## Passos

### 1. Criar manifest

`plugins/marketplace/meu_plugin/plugin.yaml`:

```yaml
name: meu_plugin
version: 1.0.0
description: Publicação em Minha Plataforma
platform: minha_plataforma
entry: plugin:MeuPlugin
hooks:
  - post_publish
```

### 2. Implementar plugin

`plugins/marketplace/meu_plugin/plugin.py`:

```python
from contentos_shared.plugins.protocol import PlatformPlugin

class MeuPlugin(PlatformPlugin):
    name = "meu_plugin"

    async def publish(self, video_meta: dict, credentials: dict) -> dict:
        return {"status": "dry_run", "platform": "minha_plataforma"}
```

### 3. Instalar / habilitar

Via API:

```http
POST /api/v1/plugins/marketplace/meu_plugin/install
POST /api/v1/plugins/meu_plugin/enable
```

Ou dashboard em `/plugins`.

### 4. Configurar credenciais

Canal em `/api/v1/channels` com `platform: minha_plataforma` e `credentials` JSON.

### 5. Modo seguro

Por padrão `PUBLISH_MODE=dry_run` — valida metadados sem postar.

### 6. Testar

```powershell
pytest tests/test_plugin_marketplace.py tests/test_plugins.py -v
```

## Checklist

- [ ] `plugin.yaml` válido
- [ ] Implementa `PlatformPlugin`
- [ ] Aparece em `GET /api/v1/plugins/marketplace`
- [ ] Install + enable funcionam
- [ ] Publisher chama hook em pipeline E2E (dry_run)
