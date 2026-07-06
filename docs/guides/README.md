# Guias de Extensão — ContentOS V2

Passo a passo para estender o ContentOS sem alterar o núcleo do pipeline.

| Guia | Quando usar |
|------|-------------|
| [ADD_PROVIDER.md](./ADD_PROVIDER.md) | Novo backend de IA (texto, voz, legendas, imagem, vision, embedding) |
| [ADD_CONTENT_SOURCE.md](./ADD_CONTENT_SOURCE.md) | Nova fonte de clips (RSS, API, biblioteca) |
| [ADD_PLUGIN.md](./ADD_PLUGIN.md) | Nova plataforma de publicação ou hook |
| [ADD_AGENT.md](./ADD_AGENT.md) | Novo step/agente no workflow |

**Regra:** agentes nunca se comunicam entre si — sempre via Workflow Engine + callback.

**Naming:** ver [NAMING.md](../NAMING.md) para mapa missão → código (`ContentSourceManager` = `SourceManager`, etc.).

**Trocar modelos de IA:** dashboard `/models` ou `PATCH /api/v1/models/{agent}` — o AI Gateway resolve via `RoutingService` quando `agent=` é enviado.

