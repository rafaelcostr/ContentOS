# Como adicionar um Agente (pipeline step)

## Visão

```
Workflow Engine → Celery queue → AgentHandler → callback → advance_pipeline
```

## Passos

### 1. Enum e fila

Em `packages/shared/src/contentos_shared/enums.py`, adicione ao `PipelineStep` se for step de pipeline.

Em `services/workflow-engine/src/contentos_workflow/tasks.py`:

```python
"contentos.meu_step.*": {"queue": "contentos.meu_step"},
```

Em `services/workflow-engine/src/contentos_workflow/engine.py`, adicione em `STEP_QUEUE_MAP`:

```python
"meu_step": "contentos.meu_step",
```

### 2. Handler

`services/agents-worker/src/contentos_agents/handlers/meu_step.py`:

```python
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput

class MeuStepHandler(BaseAgentHandler):
    step = "meu_step"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        ...
```

Para agents que também rodam async (fora do pipeline), estenda `PipelineAwareHandler` em `_pipeline_base.py`.

### 3. Registrar worker

`services/agents-worker/src/contentos_agents/worker.py`:

```python
HANDLERS = {
    ...
    "meu_step": MeuStepHandler(),
}
```

Inclua a fila no `CMD` do `docker/Dockerfile.agent` (`-Q ...,contentos.meu_step,...`). Sem isso o step nunca é consumido.


### 4. Prompt (opcional)

`packages/prompts/prompts/meu_step.md` — carregado via Prompt Manager.

### 5. Model config (opcional)

Seed em Model Manager ou via dashboard `/models`.

### 6. Workflow template

Adicione o step em `packages/shared/src/contentos_shared/workflow_templates.py` ou crie template custom no DB (`workflows` table).

API:

```http
GET /api/v1/workflows
POST /api/v1/projects/{id}/pipelines
{ "topic": "...", "workflow_name": "meu-workflow" }
```

### 7. Dashboard

Labels em `apps/dashboard/src/lib/pipeline-steps.ts`.

### 8. Testar

```powershell
pytest tests/test_agents.py -v
# E2E com stack local:
python scripts/e2e_pipeline.py
```

## Checklist

- [ ] Step no enum + STEP_QUEUE_MAP + Celery route
- [ ] Handler registrado em `worker.py`
- [ ] Callback HTTP para workflow-engine
- [ ] Prompt `.md` se usar LLM
- [ ] Template de workflow atualizado
- [ ] Label no dashboard
