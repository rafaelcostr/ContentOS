# OAuth Platform Analytics — V5.4.1

Métricas reais pós-publicação via OAuth para **YouTube**, **TikTok** e **Instagram**.

## Componentes

| Peça | Local |
|------|--------|
| Scopes analytics OAuth | `contentos_shared/oauth_providers.py` |
| Fetchers por plataforma | `intelligence/application/platform_analytics/fetchers.py` |
| Sync service | `intelligence/application/platform_analytics/service.py` |
| Snapshots DB | `platform_analytics_snapshots` |
| API | `/api/v1/analytics/platforms/*` |
| Dashboard | seção em `/analytics` |

## Scopes adicionais (quando `PLATFORM_ANALYTICS_ENABLED=true`)

| Plataforma | Scopes extras |
|------------|----------------|
| YouTube | `yt-analytics.readonly` |
| TikTok | `user.info.basic`, `user.info.stats`, `video.list` |
| Instagram | `instagram_manage_insights` |

Canais conectados **antes** desta entrega precisam **reconectar** em `/plugins` para obter os novos scopes.

## API

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/analytics/platforms?project_id=` | Capacidades + canais conectados |
| POST | `/analytics/platforms/sync` | Sincroniza todos os canais do projeto |
| POST | `/analytics/platforms/channels/{id}/sync` | Sincroniza um canal |
| GET | `/analytics/platforms/snapshots?project_id=` | Histórico de snapshots |
| GET | `/analytics/platforms/summary?project_id=` | Totais agregados por plataforma |

## Métricas normalizadas

Cada mídia retorna: `views`, `likes`, `comments`, `shares`, `engagement_rate`, `published_at`, `url`.

## Variáveis de ambiente

```env
PLATFORM_ANALYTICS_ENABLED=true
PLATFORM_ANALYTICS_MEDIA_LIMIT=10
```

Credenciais OAuth existentes: `YOUTUBE_CLIENT_*`, `TIKTOK_CLIENT_*`, `META_APP_*`.

## Testes

```powershell
pytest tests/test_platform_analytics.py -q
```

## Próximo

**V5.4.2** — Performance Learning (CTR, retenção → KB).
