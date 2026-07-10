# Growth Readiness

Este guia mostra o que ainda precisa ser configurado manualmente para o Growth OS publicar e analisar perfis reais.

## Diagnóstico automático

Rode na raiz do projeto:

```powershell
python scripts/check_growth_readiness.py
```

Com o backend ativo, também existe a rota autenticada:

```text
GET /api/v1/growth/readiness
```

O diagnóstico verifica:

- credenciais OAuth configuradas no ambiente;
- `OAUTH_REDIRECT_URI`;
- `PUBLISH_MODE`;
- plataformas com publicação real suportada;
- pontos que dependem de aprovação manual das plataformas.

## Variáveis principais

```env
OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/oauth/callback
PUBLISH_MODE=dry_run
PLATFORM_ANALYTICS_ENABLED=true

YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_API_KEY=

TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=

META_APP_ID=
META_APP_SECRET=
```

## O que ainda é manual

YouTube:

- criar projeto no Google Cloud;
- habilitar YouTube Data API v3;
- habilitar YouTube Analytics API;
- configurar OAuth consent screen;
- cadastrar `OAUTH_REDIRECT_URI`;
- gerar `YOUTUBE_CLIENT_ID` e `YOUTUBE_CLIENT_SECRET`.

TikTok:

- criar app no TikTok for Developers;
- habilitar Login Kit e Content Posting API;
- cadastrar `OAUTH_REDIRECT_URI`;
- solicitar permissões de upload/publicação quando necessário;
- gerar `TIKTOK_CLIENT_KEY` e `TIKTOK_CLIENT_SECRET`.

Instagram/Meta:

- criar app no Meta for Developers;
- vincular Instagram Business ou Creator a uma página Facebook;
- habilitar Instagram Graph API;
- aprovar permissões de publicação, página e insights;
- cadastrar `OAUTH_REDIRECT_URI`;
- gerar `META_APP_ID` e `META_APP_SECRET`.

## Sequência segura

1. Mantenha `PUBLISH_MODE=dry_run`.
2. Preencha as credenciais OAuth no `.env`.
3. Reinicie o backend.
4. Rode `python scripts/check_growth_readiness.py`.
5. Conecte os canais pela tela de Canais/Publicação.
6. Rode a auditoria OAuth do projeto em `/api/v1/growth/oauth-audit`.
7. Teste uma publicação em `prepare_only`.
8. Use `live` apenas depois de validar OAuth, qualidade do vídeo e políticas das plataformas.
