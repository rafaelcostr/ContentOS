# Mapa de correcoes e melhorias do ContentOS

Este mapa organiza o caminho para transformar a linha de montagem completa em um produto pronto para producao.

## Reauditoria pos-fases 1-7

Data: 2026-07-07.

### O que voce ja avancou

- A linha `factory-full` tem 31 steps executaveis com contrato em `factory_map.py`, `factory_truth.py`, worker handlers, filas e eventos.
- A tabela unica da fabrica existe em `docs/FACTORY_TRUTH_TABLE.md`.
- Existem modulos V5 para media real, media analyze, take recommendation, retention post-render, SEO, AI Director, Creative Memory, Performance Learning, Platform Analytics, Command Center, SLO e hardening.
- Publisher ja separa `dry_run`, `prepare_only` e `live`, tem gate de QA e registra tentativas em `platform_publications`.
- Learning/Analytics ja geram feedback de performance e recomendacoes de proximos videos.
- Dashboard ja possui secoes novas para learning, assets, factory, director, retention, seo, creative memory, voice e operacao.

### O que ainda falta para ficar realmente pronto

- Provar E2E real com stack completa: Postgres, Redis, MinIO, FFmpeg, Piper/Whisper/Ollama, fontes de midia e OAuth.
- Transformar os pontos `partial` em `ready`: `clip_research`, `asset_collector`, `thumbnail` e `publisher`.
- Substituir ou isolar stubs restantes, especialmente catalogos licenciados ainda marcados como stub.
- Fortalecer thumbnail com validacao visual e rejeicao de placeholder em producao.
- Completar smoke/load/pentest em ambiente production-like, nao apenas testes unitarios.
- Garantir migrations aplicadas ate `022_platform_publications` e validar rollback/restore.
- Revisar secrets, logs, SSRF/download externo, RBAC por projeto e CORS antes de publicar trafego real.

## Novo mapa de fases

### Nova Fase 1 - Consolidacao de contrato e documentacao

Objetivo: eliminar divergencias entre docs, codigo e testes.

- Corrigir lint/imports em arquivos novos.
- Alinhar `docs/FACTORY_MAP.md` com a ordem real `quality -> retention`.
- Adicionar teste para impedir que o mapa publico volte a divergir da ordem executavel.
- Rodar contratos da fabrica e testes focados.

Status: **em andamento**.

### Nova Fase 2 - Fechar etapas parciais da fabrica

Objetivo: transformar `clip_research`, `asset_collector`, `thumbnail` e `publisher` de parcial para pronto.

- Testar fontes Pexels/Pixabay/biblioteca propria com licenca, duracao e deduplicacao.
- Definir fallback controlado quando nao houver midia por cena.
- Criar QA de thumbnail com tamanho, contraste, texto e ausencia de placeholder em producao.
- Validar upload real por plataforma em staging com OAuth.

### Nova Fase 3 - E2E real production-like

Objetivo: provar que a linha gera um MP4 publicavel de ponta a ponta.

- Subir Postgres, Redis, MinIO, workers e gateway.
- Rodar `scripts/e2e_pipeline.py` com `factory-full`.
- Verificar assets, voz, legenda, render, QA, retry, SEO e publisher em `prepare_only`.
- Salvar artefatos e relatorio por pipeline.

### Nova Fase 4 - Pentest aplicado

Objetivo: reduzir risco operacional antes de `live`.

- Auditar SSRF em downloads e URLs externas.
- Auditar upload/asset serving, tokens OAuth, logs e erros.
- Validar RBAC por organizacao/projeto nas rotas novas.
- Testar rate limit, CORS e headers.

### Nova Fase 5 - Observabilidade e operacao

Objetivo: conseguir operar a fabrica com fila, custo, falha e retry visiveis.

- Validar `/metrics`, `/health/ready` e `/ops/slo`.
- Verificar dashboards e alertas Prometheus.
- Rodar load test em staging.
- Conferir KEDA e pools de worker por etapa.

### Nova Fase 6 - Go-live assistido

Objetivo: liberar publicacao real gradualmente.

- Rodar pilotos com `prepare_only`.
- Revisar manualmente os primeiros renders e thumbnails.
- Promover uma plataforma por vez para `live`.
- Monitorar analytics, performance learning e recomendacoes apos publicacao.

## Fase 1 - Base consistente

Objetivo: garantir que o codigo esteja limpo o suficiente para evoluir sem divergencia entre pipeline, mapa da fabrica, dashboard e testes.

- Corrigir lint automatico e imports mortos.
- Remover codigo morto simples detectado pelo lint.
- Alinhar `factory_map.py` com as 31 etapas executaveis de `PipelineStep.factory_full_ordered()`.
- Criar contrato de teste para impedir que o mapa oficial fique diferente da pipeline real.
- Registrar este mapa de fases.

## Fase 2 - Documentacao e fonte unica da fabrica

Objetivo: fazer README, docs e dashboard contarem a mesma historia da fabrica.

- Atualizar README com a sequencia oficial de 31 etapas.
- Atualizar documentos que ainda citam 27, 29 ou 30 etapas.
- Revisar `docs/FACTORY_MAP.md`, `docs/CONTENT_FACTORY.md`, `docs/AI_DIRECTOR.md`, `docs/RETENTION_ENGINE.md` e `docs/SEO_ENGINE.md`.
- Criar uma tabela unica com etapa, modulo, handler, fila, evento, status e dependencia externa. **Feito:** `docs/FACTORY_TRUTH_TABLE.md` + `scripts/generate_factory_truth_table.py`.

## Fase 3 - Validacao automatica da esteira

Objetivo: provar que a linha de montagem nao apenas existe, mas roda de forma previsivel.

- Rodar a suite de testes Python completa.
- Corrigir testes quebrados sem mascarar falhas reais.
- Adicionar teste de contrato para handler, fila e evento de cada etapa do `factory-full`.
- Adicionar teste de template para garantir que `factory-full` sempre use a ordem oficial.
- Validar migracoes e modelos de banco relacionados a V5.

## Fase 4 - Media pipeline real

Objetivo: reduzir placeholders e garantir que cada cena receba midia autorizada e suficiente.

- Validar chaves e limites de Pexels/Pixabay.
- Garantir duracao minima por cena.
- Melhorar deduplicacao, score e fallback de assets.
- Reprovar etapa quando nao houver midia suficiente, em vez de aceitar placeholder silencioso em producao. **Feito:** `MEDIA_REQUIRE_ASSETS` / `MEDIA_REQUIRE_CLIPS` / `RENDER_ALLOW_PLACEHOLDER` em `media_production.py`; falha em `asset_collector`, `takes`, `editor` e `ffmpeg_provider`; placeholders sinteticos so em dev.
- Registrar licenca, origem, autor e URL de cada asset usado.

## Fase 5 - Render, voz, legenda e QA audiovisual

Objetivo: garantir que o video final seja publicavel.

- Testar render real com FFmpeg em 9:16.
- Validar sincronizacao de voz e legenda.
- Validar volume, musica, cortes, zooms, transicoes e barra de progresso.
- Criar amostras de QA automatico por resolucao, FPS, bitrate, duracao e audio.
- Criar criterios claros de aprovado/reprovado para `quality`, `retention` e `video_review`. **Feito (parcial):** `audiovisual_qa.py` com gate unificado `publishable`; sync SRT + bitrate em `quality_scoring`; testes em `test_audiovisual_qa.py` + `test_ffmpeg_integration.py`.

## Fase 6 - Publisher e plataformas

Objetivo: sair de dry-run para publicacao real controlada.

- Finalizar upload binario real para YouTube quando usado upload resumivel.
- Validar OAuth, escopos, refresh token e erros de plataforma.
- Separar claramente `dry_run`, `prepare_only` e `live`. **Feito:** `normalize_publish_mode()` + `GET /publish/status` tri-state.
- Adicionar testes com mocks para YouTube, TikTok e Instagram. **Feito (parcial):** chunked YouTube + Instagram `render_public_url` em `test_plugins.py`.
- Registrar URL final, ID externo, status e falhas de cada publicacao. **Feito:** tabela `platform_publications` + `GET /api/v1/publish/attempts` + persist no publisher + UI `PublishAttempts` em `/plugins` (histórico embutido em Conectar plataformas).

## Fase 7 - Memoria, learning e analytics reais

Objetivo: fazer o sistema aprender com dados reais de performance.

- Validar persistencia de Knowledge Base e Creative Memory com banco real.
- Conectar analytics reais das plataformas quando houver token autorizado.
- Relacionar performance com hook, roteiro, thumbnail, duracao, nicho e CTA.
- Criar loop de recomendacao para proximos videos. **Feito:** `GET /api/v1/projects/{id}/recommendations` + secao em `/learning`.
- Retencao pos-render com duracao real do MP4. **Feito:** `retention` apos `quality`; `post_render.py` + penalidades por QA/render.

## Fase 8 - Pentest e hardening

Objetivo: proteger o sistema antes de uso em producao.

- Revisar autenticacao, autorizacao e acesso por projeto.
- Validar uploads, downloads externos e protecao contra SSRF.
- Proteger tokens, OAuth secrets e credenciais de provedores.
- Revisar CORS, rate limit, headers e logs sensiveis.
- Validar plugins de publicacao em sandbox ou camada controlada.
- Remover placeholders de secrets em Kubernetes ou migrar para External Secrets.

## Fase 9 - Operacao e observabilidade

Objetivo: operar a fabrica com confianca.

- Padronizar dashboards de filas, custos, erros, retries e tempo por etapa.
- Definir SLOs reais por pipeline e por fila.
- Completar alertas e runbooks.
- Testar autoscaling KEDA com carga.
- Criar relatorio de producao por projeto e por plataforma.

## Fase 10 - Producao assistida

Objetivo: validar o sistema com videos reais antes de automacao total.

- Rodar pilotos com poucos projetos e temas controlados.
- Comparar resultado automatico contra revisao humana.
- Ajustar prompts, thresholds e retry.
- Liberar publicacao automatica apenas depois de aprovacao consistente.
