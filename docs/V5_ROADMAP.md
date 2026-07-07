# ContentOS V5 — Roadmap de Autonomia Total

| Campo | Valor |
|-------|--------|
| **Visão** | Usuário informa tema — produção, qualidade, publicação e aprendizado automáticos |
| **Base** | [V5_CONSOLIDATION_MAP.md](./V5_CONSOLIDATION_MAP.md) |
| **Decisões** | [ADR.md](./ADR.md) — ADR-009 (Media Acquisition) |
| **V4 concluído** | [V4_ROADMAP.md](./V4_ROADMAP.md) |
| **Regra** | 100% aditivo. Nunca quebrar V1–V4. Aprovação humana entre fases. |

---

## Legenda de status

| Símbolo | Significado |
|---------|-------------|
| **DONE** | Implementado e testado |
| **WIP** | Em andamento |
| **TODO** | Pendente |
| **SKIP** | Fora de escopo (ex.: scrape TikTok) |

---

## Visão das fases

```
V5.0 Autonomia de Mídia → V5.1 Estúdio → V5.2 Qualidade Autônoma
        → V5.3 Content Factory → V5.4 Pós-Publicação → V5.5 Produção Enterprise
```

---

## Fase V5.0 — Autonomia de mídia

**Objetivo:** tema → vídeo montado com B-roll licenciado, sem intervenção manual.

| ID | Entrega | Status | Doc / código |
|----|---------|--------|--------------|
| **V5.0.1** | Pexels + Pixabay adapters, DownloadPipeline, licença | **DONE** | `content-sources/adapters/pexels.py`, `pixabay.py` |
| **V5.0.2** | `asset_collector` top-N por cena | **DONE** | `handlers/asset_collector.py` |
| **V5.0.3** | Step `media_analyze` — vision tags + embeddings | **DONE** | `handlers/media_analyze.py` |
| **V5.0.4** | `TakeRecommendationService` — upgrade asset_search/takes | **DONE** | `intelligence/application/take_recommendation/` |
| **V5.0.5** | Template `v5-media-autopilot` + E2E GTA 6 | **DONE** | `workflow_templates.py`, `test_v5_media_autopilot.py` |
| **V5.0.6** | Dashboard assets semântico | **DONE** | `/assets` + `GET /assets/search/semantic` |

**Critério de saída V5.0:** E2E tema → MP4 com ≥2 clips reais, narração e legendas.

```powershell
pytest tests/test_media_acquisition.py tests/test_content_sources.py -q
```

---

## Fase V5.1 — Estúdio

**Objetivo:** voz profissional + edição cinematográfica v1.

| ID | Entrega | Status |
|----|---------|--------|
| **V5.1.1** | Voice Profiles + speed/pitch/pause | **DONE** | `contentos_shared/voice/`, `voice_profiles` API |
| **V5.1.2** | Voice Library por projeto | **DONE** | `/voice-library` + `projects/{id}/voice-library` |
| **V5.1.3** | Cinematic Editor v1 (zoom, speed ramp, ducking) | **DONE** | `cinematic/`, `ffmpeg_filters`, `editor` handler |
| **V5.1.4** | Project DNA 2.0 | **DONE** | `dna_v2`, `dna/pipeline_hints`, workflow inject |
| **V5.1.5** | Dashboard `/voice-studio` | **DONE** | editor visual + preview TTS + pipeline payload |

---

## Fase V5.2 — Qualidade autônoma

**Objetivo:** sistema se corrige antes de publicar.

| ID | Entrega | Status |
|----|---------|--------|
| **V5.2.1** | Retention Engine (análise segundo a segundo) | **DONE** | `retention` agent, `RetentionAnalyzer`, `/retention` |
| **V5.2.2** | Retention → auto_retry (hook, take, CTA) | **DONE** |
| **V5.2.3** | SEO Engine (títulos, hashtags, descrições) | **DONE** |
| **V5.2.4** | AI Director v1 (re-run parcial por score) | **DONE** |
| **V5.2.5** | Creative Memory (merge KB + Learning) | **DONE** |

---

## Fase V5.3 — Content Factory

**Objetivo:** N vídeos por tema em lote agendado.

| ID | Entrega | Status |
|----|---------|--------|
| **V5.3.1** | `BatchProductionService` | **DONE** |
| **V5.3.2** | Variação automática hook/ângulo | **DONE** |
| **V5.3.3** | Quotas e custo por lote | **DONE** |
| **V5.3.4** | Dashboard `/factory` | **DONE** |
| **V5.3.5** | Aprovação humana opcional antes de publicar lote | **DONE** |

Ver [CONTENT_FACTORY.md](./CONTENT_FACTORY.md).

---

## Fase V5.4 — Pós-publicação

**Objetivo:** aprender com métricas e comentários reais.

| ID | Entrega | Status |
|----|---------|--------|
| **V5.4.1** | OAuth Analytics (TikTok, YouTube, Instagram) | **DONE** |
| **V5.4.2** | Performance Learning (CTR, retenção → KB) | **DONE** |
| **V5.4.3** | Comment Analyzer | **DONE** |
| **V5.4.4** | Community Agent v1 (rascunhos, sem auto-post) | **DONE** |

---

## Fase V5.5 — Produção enterprise

**Objetivo:** escala, observabilidade, go-live.

| ID | Entrega | Status |
|----|---------|--------|
| **V5.5.1** | Command Center (evoluir `/executive`) | **DONE** |
| **V5.5.2** | Workers KEDA em produção | **DONE** |
| **V5.5.3** | SLO, alertas, runbooks | **DONE** |
| **V5.5.4** | Testes de carga + hardening | **DONE** |
| **V5.5.5** | `PRODUCTION_READY.md` + checklist | **DONE** |

**Fase V5.5 concluída.** Roadmap V5 completo (V5.0–V5.5).

---

## Fora de escopo (lista negra)

- Scrape TikTok / snaptik / download sem licença
- Reimplementar AI Gateway, Workflow Engine, Asset Manager, Billing, RBAC
- Community auto-post sem moderação
- Vision em todo frame de todo vídeo

---

## Como avançar

1. Você aprova o ID (ex.: `autorizado V5.0.1`).
2. Agente: impacto → ADR se necessário → código → testes → docs → Swagger/dashboard.
3. Atualiza status neste documento.
4. Para e espera próxima aprovação.

---

## Próxima implementação

**V5 concluído.** Novos epics (V6+) requerem ADR e novo roadmap.

Checklist de go-live: [PRODUCTION_READY.md](./PRODUCTION_READY.md).
