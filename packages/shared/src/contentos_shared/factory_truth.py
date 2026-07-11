"""Factory truth table — single source for step metadata (docs + tests)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contentos_events.domain.event_types import STEP_TO_DOMAIN_EVENT

from contentos_shared.enums import PipelineStep
from contentos_shared.factory_map import FACTORY_LINE, FactoryStage

# External runtime dependency per executable step (provider / service).
STEP_EXTERNAL_DEPS: dict[str, str] = {
    "trend_intelligence": "rules+postgres",
    "research": "ollama",
    "hook": "ollama",
    "script": "ollama",
    "script_review": "ollama",
    "scene": "ollama",
    "storyboard": "ollama",
    "scene_director": "rules",
    "asset_index": "postgres+minio",
    "media_analyze": "ollama+minio",
    "asset_search": "postgres",
    "takes": "minio",
    "voice": "piper",
    "subtitle": "whisper",
    "editor": "ffmpeg+minio",
    "thumbnail": "ollama+image",
    "retention": "rules+ffprobe",
    "quality": "ffprobe",
    "video_review": "ollama",
    "auto_retry": "rules+workflow-engine",
    "content_score": "rules",
    "ai_director": "rules",
    "content_intelligence": "rules",
    "learning": "rules+postgres",
    "knowledge_base": "postgres",
    "creative_memory": "rules+postgres",
    "analytics": "ollama+postgres",
    "seo": "ollama",
    "publisher": "ollama+oauth-plugins",
}


@dataclass(frozen=True)
class FactoryTruthRow:
    order: int
    step: str
    title: str
    module: str
    status: str
    handler: str
    queue: str
    event: str
    external_dep: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "step": self.step,
            "title": self.title,
            "module": self.module,
            "status": self.status,
            "handler": self.handler,
            "queue": self.queue,
            "event": self.event,
            "external_dep": self.external_dep,
        }


def _stage_for_step(step: PipelineStep) -> FactoryStage | None:
    for stage in FACTORY_LINE:
        if stage.pipeline_step == step:
            return stage
    return None


def build_factory_truth_rows() -> list[FactoryTruthRow]:
    rows: list[FactoryTruthRow] = []
    for index, step in enumerate(PipelineStep.factory_full_ordered(), start=1):
        key = step.value
        stage = _stage_for_step(step)
        rows.append(
            FactoryTruthRow(
                order=index,
                step=key,
                title=stage.title if stage else key,
                module=stage.module if stage else "—",
                status=stage.status if stage else "ready",
                handler=f"contentos_agents.handlers.{key}",
                queue=f"contentos.{key}",
                event=STEP_TO_DOMAIN_EVENT.get(key, "step.completed"),
                external_dep=STEP_EXTERNAL_DEPS.get(key, "—"),
            )
        )
    return rows


def format_factory_truth_markdown() -> str:
    rows = build_factory_truth_rows()
    lines = [
        "# Factory Truth Table",
        "",
        "Tabela única da linha de montagem `factory-full` (29 steps executáveis).",
        "",
        "Fontes de verdade:",
        "",
        "- Ordem: `PipelineStep.factory_full_ordered()`",
        "- Mapa produto: `factory_map.py`",
        "- Contrato: `tests/test_factory_full_contract.py` + `tests/test_factory_truth_table.py`",
        "",
        "Regenerar:",
        "",
        "```bash",
        "python scripts/generate_factory_truth_table.py",
        "```",
        "",
        "| # | Step | Módulo | Status | Handler | Fila | Evento | Dependência externa |",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.order} | `{row.step}` | {row.module} | {row.status} | `{row.handler}` | `{row.queue}` | `{row.event}` | {row.external_dep} |"
        )
    lines.append("")
    return "\n".join(lines)
