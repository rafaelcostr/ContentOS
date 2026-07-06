"""Emotion Analyzer Agent — scores script emotional impact (V3 Tier B3)."""

import json

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta

SCORE_KEYS = ("emotion", "curiosity", "retention", "impact", "overall")


def _clamp_score(value, default: int = 5) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(1, min(10, score))


def _as_str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:8]


def _heuristic_scores(script: dict, hook_text: str) -> dict:
    """Fallback scores when LLM is unavailable."""
    text = " ".join(
        str(script.get(k) or "")
        for k in ("hook", "development", "curiosity", "call_to_action", "full_text")
    )
    text = f"{hook_text} {text}".strip()
    length = len(text)
    has_question = "?" in text
    has_urgency = any(w in text.lower() for w in ("agora", "hoje", "urgente", "não vai", "para tudo"))
    emotion = 6 + (1 if has_urgency else 0)
    curiosity = 7 if has_question else 5
    retention = 6 if 80 <= length <= 600 else 4
    impact = round((emotion + curiosity + retention) / 3)
    overall = round((emotion + curiosity + retention + impact) / 4)
    return {
        "emotion": _clamp_score(emotion),
        "curiosity": _clamp_score(curiosity),
        "retention": _clamp_score(retention),
        "impact": _clamp_score(impact),
        "overall": _clamp_score(overall),
        "dominant_emotion": "curiosidade" if has_question else "interesse",
        "risks": [] if length else ["Roteiro vazio"],
        "strengths": ["Heurística local"],
        "summary": "Scores estimados sem LLM",
    }


def normalize_emotion_scores(raw: dict, *, script: dict, hook_text: str) -> dict:
    data = coerce_dict(raw)
    if not data:
        return _heuristic_scores(script, hook_text)

    scores = {key: _clamp_score(data.get(key), 5) for key in SCORE_KEYS}
    if "overall" not in data or data.get("overall") in (None, ""):
        scores["overall"] = _clamp_score(
            round(sum(scores[k] for k in ("emotion", "curiosity", "retention", "impact")) / 4)
        )

    return {
        **scores,
        "dominant_emotion": str(data.get("dominant_emotion") or "interesse").strip().lower()[:40],
        "risks": _as_str_list(data.get("risks")),
        "strengths": _as_str_list(data.get("strengths")),
        "summary": str(data.get("summary") or "").strip(),
    }


class EmotionAgentHandler(BaseAgentHandler):
    step = "emotion"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        script = coerce_dict(task_input.payload.get("script"))
        topic = (
            script.get("title")
            or coerce_dict(task_input.payload.get("selected_topic")).get("title")
            or task_input.payload.get("topic", "")
        )
        logs = [f"[emotion] Scoring script for: {topic}"]

        hook = coerce_dict(task_input.payload.get("selected_hook") or task_input.payload.get("hook"))
        hook_text = (
            task_input.payload.get("hook_text")
            or hook.get("hook_text")
            or script.get("hook")
            or ""
        )
        hook_style = (
            task_input.payload.get("hook_style")
            or hook.get("style")
            or script.get("hook_style")
            or ""
        )

        if not script and not hook_text:
            scores = _heuristic_scores({}, "")
            logs.append("No script — heuristic defaults")
        else:
            prompt = self.render_prompt(
                "emotion",
                {
                    "topic": topic,
                    "script_json": json.dumps(script, ensure_ascii=False)[:4000],
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
                scores = normalize_emotion_scores(coerce_dict(raw), script=script, hook_text=hook_text)
            except Exception as exc:
                logs.append(f"LLM fallback: {exc}")
                scores = _heuristic_scores(script, hook_text)

        logs.append(
            "Scores "
            f"emotion={scores['emotion']} curiosity={scores['curiosity']} "
            f"retention={scores['retention']} impact={scores['impact']} "
            f"overall={scores['overall']}"
        )
        if scores.get("summary"):
            logs.append(scores["summary"])

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(scores, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="emotion.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "emotion": scores,
                "emotion_scores": scores,
                "emotion_overall": scores["overall"],
            },
            logs=logs,
        )
