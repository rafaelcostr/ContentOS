# Voice Studio — V5.1

Controles profissionais de narração no pipeline `voice`.

## Voice Profiles (V5.1.1)

Perfis reutilizáveis com:

| Campo | Faixa | Default |
|-------|-------|---------|
| `speed` | 0.5 – 2.0 | 1.0 |
| `pitch_semitones` | -12 – +12 | 0 |
| `pause_ms` | 0 – 2000 | 300 |

### Built-ins

| Nome | Uso |
|------|-----|
| `default` | Narração equilibrada |
| `hype` | Mais rápido, pausas curtas |
| `calm` | Mais lento, pausas longas |
| `documentary` | Tom documentário |

### Pipeline

1. `resolve_voice_profile()` — payload, DB ou built-in
2. `synthesize_narration()` — TTS por frase + pausas FFmpeg
3. `apply_speed_pitch()` — pós-processamento FFmpeg

Ordem de resolução do perfil:

1. `payload.voice_profile` (dict inline)
2. `payload.voice_profile_id` (tabela `voice_profiles`)
3. Perfil default do projeto (`is_default=true`)
4. `payload.voice_profile_name` ou `DEFAULT_VOICE_PROFILE`

### API

```
GET    /api/v1/voice-profiles/builtins
GET    /api/v1/voice-profiles?project_id=
POST   /api/v1/voice-profiles
POST   /api/v1/voice-profiles/preview
GET    /api/v1/voice-profiles/{id}
PATCH  /api/v1/voice-profiles/{id}
DELETE /api/v1/voice-profiles/{id}
```

### Environment

```env
DEFAULT_VOICE_PROFILE=default
ENABLE_VOICE_PROFILES=true
```

### Componentes

| Classe | Path |
|--------|------|
| `VoiceProfileSettings` | `shared/voice/profile.py` |
| `synthesize_narration` | `shared/voice/narration.py` |
| `VoiceAgentHandler` | `agents-worker/handlers/voice.py` |
| `VoiceProfileService` | `gateway/services/voice_profile_service.py` |

### Tests

```bash
pytest tests/test_voice_profile.py -q
```

## Voice Library por projeto (V5.1.2)

Cada projeto tem uma biblioteca unificada:

- **Built-ins** — `default`, `hype`, `calm`, `documentary`
- **Custom** — perfis salvos em `voice_profiles` com `project_id`
- **Default** — perfil custom (`is_default`) ou built-in (`project_memory.default_voice_builtin`)

O workflow engine injeta `voice_profile_id` ou `voice_profile_name` no payload do step `voice` quando o pipeline não define um perfil explicitamente.

### API

```
GET /api/v1/projects/{id}/voice-library
PUT /api/v1/projects/{id}/voice-library/default
POST /api/v1/projects/{id}/voice-library/clone
```

### Dashboard

`/voice-library` — selecionar projeto, definir padrão, clonar built-in, criar custom.

```bash
pytest tests/test_voice_library.py -q
```

## Voice Studio dashboard (V5.1.5)

Dashboard unificado em `/voice-studio` (substitui `/voice-library`):

| Área | Função |
|------|--------|
| **Biblioteca** | Built-ins + custom do projeto, perfil padrão |
| **Editor** | Sliders speed / pitch / pause, salvar, clonar, excluir |
| **Preview** | `POST /voice-profiles/preview` — ouvir amostra TTS |
| **Pipeline** | Preview do payload injetado no step `voice` |

`/voice-library` redireciona para `/voice-studio`.

```bash
pytest tests/test_voice_studio.py tests/test_voice_library.py -q
```
