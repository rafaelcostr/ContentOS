# Comment Analyzer — V5.4.3

Analisa **comentários reais** de vídeos publicados (via OAuth V5.4.1), extrai sentimento e temas, opcionalmente indexa na KB.

## Fluxo

```
PlatformAnalyticsSnapshot (media_id)
        +
Channel OAuth credentials
        ↓
Fetch comments (YouTube / Instagram / TikTok*)
        ↓
Sentiment + themes (rules-based)
        ↓
comment_analysis_insights (+ KB opcional)
```

\* TikTok comment API pode retornar `comments_api_unavailable` conforme permissões do app.

## API

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/comment-analyzer/analyze` | Analisa comentários das mídias do projeto |
| GET | `/api/v1/comment-analyzer/insights?project_id=` | Histórico |

## Métricas por mídia

- `positive_pct`, `negative_pct`, `neutral_pct`
- `question_count` — comentários com `?`
- `themes` — palavras frequentes
- `sample_comments` — até 5 exemplos

## Variáveis de ambiente

```env
COMMENT_ANALYZER_ENABLED=true
COMMENT_ANALYZER_MAX_COMMENTS=50
COMMENT_ANALYZER_AUTO_INDEX_KB=false
```

## Dashboard

`/learning` — botão **Comment Analyzer** e lista de insights.

## Testes

```powershell
pytest tests/test_comment_analyzer.py tests/test_performance_learning.py -q
```

## Próximo

**V5.4.4** — Community Agent v1 (rascunhos, sem auto-post).
