# ContentOS — Plugin System

## Objetivo

Publicar em TikTok, YouTube Shorts e Instagram Reels **sem alterar o núcleo** — Strategy Pattern via `PublishPlugin`.

---

## Arquitetura

```
PublisherAgentHandler
    ↓
PublishContext (topic, script, render_ref, credentials)
    ↓
PluginRegistry → TikTokPlugin | YouTubeShortsPlugin | InstagramReelsPlugin
    ↓
prepare() → format metadata per platform
publish() → dry_run (default) | live (with credentials)
    ↓
publication.json → MinIO + Video record
```

---

## Plugins implementados

| Plugin | Plataforma | Regras |
|--------|------------|--------|
| `TikTokPlugin` | TikTok | Título ≤150 chars, 5 hashtags |
| `YouTubeShortsPlugin` | YouTube | #Shorts automático, título ≤100 |
| `InstagramReelsPlugin` | Instagram | Caption ≤2200, 30 hashtags |

---

## Modos de publicação

```env
PUBLISH_MODE=dry_run    # default — prepara metadados + preview URL
PUBLISH_MODE=live       # tenta upload real via API da plataforma

ENABLED_PLATFORMS=tiktok,youtube,instagram
```

### Credenciais (live)

Via env JSON:

```env
PLATFORM_CREDENTIALS_JSON={"tiktok":{"access_token":"..."},"youtube":{"access_token":"...","api_key":"..."},"instagram":{"access_token":"...","instagram_user_id":"..."}}
```

Ou via API:

```
POST /api/v1/channels
{
  "project_id": "...",
  "platform": "tiktok",
  "name": "Meu TikTok",
  "credentials": {"access_token": "..."}
}
```

---

## API

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/v1/plugins` | Lista plugins + modo + enabled |
| `GET /api/v1/plugins/{name}` | Detalhe do plugin |
| `GET /api/v1/channels` | Canais configurados |
| `POST /api/v1/channels` | Criar canal com credenciais |

---

## Criar novo plugin

1. Estenda `PublishPlugin` em `plugins/platforms/`
2. Implemente `prepare()` e `_publish_live()`
3. Registre em `plugins/loader.py`
4. Adicione à env `ENABLED_PLATFORMS`

O Workflow Engine e os outros agentes **não mudam**.

---

## Dashboard

http://localhost:3000/plugins — status dos plugins e configuração.

---

## Status

| Plugin | Status |
|--------|--------|
| TikTok | ✅ Fase 5 |
| YouTube Shorts | ✅ Fase 5 |
| Instagram Reels | ✅ Fase 5 |
| Telegram | ⬜ futuro |
| Discord | ⬜ futuro |
