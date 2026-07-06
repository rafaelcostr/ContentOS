"""Script Reviewer Agent — improves draft scripts (V3 Tier B2)."""

import json

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta

SCRIPT_KEYS = (
    "title",
    "hook",
    "development",
    "curiosity",
    "call_to_action",
    "full_text",
    "duration_seconds",
)


def _clamp_score(value, default: int = 5) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(10, score))


def _normalize_script(raw: dict, fallback: dict) -> dict:
    script = coerce_dict(raw.get("script") if "script" in raw else raw)
    out = dict(fallback)
    for key in SCRIPT_KEYS:
        if key in script and script[key] not in (None, ""):
            out[key] = script[key]
    # duration bounds
    try:
        duration = float(out.get("duration_seconds", 45))
    except (TypeError, ValueError):
        duration = 45.0
    out["duration_seconds"] = max(30, min(60, duration))
    if not out.get("full_text"):
        parts = [out.get("hook"), out.get("development"), out.get("curiosity"), out.get("call_to_action")]
        out["full_text"] = " ".join(str(p) for p in parts if p)
    return out


def _normalize_review(raw: dict, original: dict) -> dict:
    data = coerce_dict(raw)
    script = _normalize_script(data, original)
    changes = data.get("changes")
    if not isinstance(changes, list):
        changes = []
    changes = [str(c).strip() for c in changes if str(c).strip()][:10]
    return {
        "script": script,
        "changes": changes,
        "score_before": _clamp_score(data.get("score_before"), 5),
        "score_after": _clamp_score(data.get("score_after"), 7),
        "summary": str(data.get("summary") or "").strip(),
    }


class ScriptReviewAgentHandler(BaseAgentHandler):
    step = "script_review"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        original = coerce_dict(task_input.payload.get("script"))
        topic = (
            original.get("title")
            or coerce_dict(task_input.payload.get("selected_topic")).get("title")
            or task_input.payload.get("topic", "")
        )
        logs = [f"[script_review] Reviewing script for: {topic}"]

        if not original:
            logs.append("No draft script — skipping review")
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.COMPLETED.value,
                data={"script": {}, "script_review": {"skipped": True}},
                logs=logs,
            )

        hook = coerce_dict(task_input.payload.get("selected_hook") or task_input.payload.get("hook"))
        hook_text = task_input.payload.get("hook_text") or hook.get("hook_text") or original.get("hook") or ""
        hook_style = task_input.payload.get("hook_style") or hook.get("style") or original.get("hook_style") or ""

        prompt = self.render_prompt(
            "script_review",
            {
                "topic": topic,
                "script_json": json.dumps(original, ensure_ascii=False)[:4000],
                "hook_text": str(hook_text),
                "hook_style": str(hook_style),
            },
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
            review = _normalize_review(coerce_dict(raw), original)
        except Exception as exc:
            logs.append(f"LLM fallback (keep original): {exc}")
            review = {
                "script": original,
                "changes": [],
                "score_before": 5,
                "score_after": 5,
                "summary": "Review skipped — original script kept",
            }

        improved = review["script"]
        if hook_text and not improved.get("hook"):
            improved["hook"] = hook_text
        if hook_style:
            improved["hook_style"] = hook_style

        logs.append(
            f"Scores {review['score_before']}→{review['score_after']}; "
            f"{len(review['changes'])} changes"
        )
        if review["summary"]:
            logs.append(review["summary"])

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps({"original": original, "review": review}, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="script_review.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "script": improved,
                "script_review": {
                    "changes": review["changes"],
                    "score_before": review["score_before"],
                    "score_after": review["score_after"],
                    "summary": review["summary"],
                },
                "script_original": original,
            },
            logs=logs,
        )
