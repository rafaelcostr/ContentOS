"""Hook Generator Agent — chooses best opening hook before script (V3 Tier B1)."""

import json

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta

HOOK_STYLES = ("mystery", "shock", "curiosity", "controversy", "urgency")


def _normalize_hook(raw: dict, topic: str) -> dict:
    style = str(raw.get("style") or "curiosity").lower().strip()
    if style not in HOOK_STYLES:
        style = "curiosity"
    hook_text = str(raw.get("hook_text") or raw.get("hook") or "").strip()
    if not hook_text:
        hook_text = f"Você não vai acreditar no que rolou com {topic}."
    alternatives = raw.get("alternatives")
    if not isinstance(alternatives, list):
        alternatives = []
    clean_alts = []
    for item in alternatives[:3]:
        if not isinstance(item, dict):
            continue
        alt_style = str(item.get("style") or "curiosity").lower()
        if alt_style not in HOOK_STYLES:
            alt_style = "curiosity"
        alt_text = str(item.get("hook_text") or item.get("hook") or "").strip()
        if alt_text:
            clean_alts.append({"style": alt_style, "hook_text": alt_text})
    return {
        "style": style,
        "hook_text": hook_text,
        "alternatives": clean_alts,
        "rationale": str(raw.get("rationale") or "").strip(),
    }


class HookAgentHandler(BaseAgentHandler):
    step = "hook"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        selected = coerce_dict(task_input.payload.get("selected_topic"))
        topic = selected.get("title") or task_input.payload.get("topic", "")
        logs = [f"[hook] Selecting best hook for: {topic}"]

        prompt = self.render_prompt(
            "hook",
            {"topic": topic, "context": json.dumps(selected, ensure_ascii=False)},
            project_id=task_input.project_id,
        )
        logs.append(f"Prompt v{prompt.version}")

        try:
            raw, from_cache, cache_key = await self.chat_json_with_cache(
                prompt,
                topic=topic,
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                job_id=task_input.job_id,
            )
            if from_cache:
                logs.append(f"Cache hit ({cache_key})")
            hook = _normalize_hook(coerce_dict(raw), topic)
        except Exception as exc:
            logs.append(f"LLM fallback: {exc}")
            hook = _normalize_hook({}, topic)

        logs.append(f"Selected style={hook['style']}: {hook['hook_text']}")

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(hook, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="hook.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "hook": hook,
                "selected_hook": hook,
                "hook_text": hook["hook_text"],
                "hook_style": hook["style"],
            },
            logs=logs,
        )
