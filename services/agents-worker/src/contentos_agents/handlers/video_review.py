"""Video Reviewer Agent — creative score after technical quality (V3 Tier B7)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.providers.ffmpeg_provider import FFmpegProvider
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta, AssetRef

DEFAULT_MIN_SCORE = 8


def _clamp_score(value, default: int = 5) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(1, min(10, score))


def _min_score() -> int:
    try:
        return max(1, min(10, int(os.getenv("VIDEO_REVIEW_MIN_SCORE", str(DEFAULT_MIN_SCORE)))))
    except ValueError:
        return DEFAULT_MIN_SCORE


def _as_str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:5]


def _technical_dimension(*, quality_passed: bool, quality_score: int | None) -> int:
    if quality_score is not None:
        return _clamp_score(quality_score, 8 if quality_passed else 3)
    return 8 if quality_passed else 3


def _heuristic_review(
    *,
    emotion: dict,
    quality_passed: bool,
    render_meta: dict,
    quality_score: int | None = None,
) -> dict:
    emotion_overall = _clamp_score(emotion.get("overall"), 5)
    score = emotion_overall
    if not quality_passed:
        score = min(score, 4)
    elif quality_score is not None:
        tech = _clamp_score(quality_score, 5)
        score = round((score + tech) / 2)
    duration = float(render_meta.get("duration_seconds") or 0)
    if duration and (duration < 15 or duration > 60):
        score = min(score, 6)
    suggestions: list[str] = []
    if emotion_overall < 7:
        suggestions.append("Fortalecer hook e curiosidade no início")
    if not quality_passed:
        suggestions.append("Corrigir falhas técnicas de qualidade antes de publicar")
    if duration and duration > 55:
        suggestions.append("Encurtar o vídeo para manter retenção")
    return {
        "score": _clamp_score(score),
        "passed": score >= _min_score(),
        "dimensions": {
            "hook": _clamp_score(emotion.get("curiosity"), score),
            "pacing": _clamp_score(emotion.get("retention"), score),
            "emotion": _clamp_score(emotion.get("emotion"), score),
            "cta": _clamp_score(emotion.get("impact"), score),
            "technical": _technical_dimension(quality_passed=quality_passed, quality_score=quality_score),
        },
        "suggestions": suggestions,
        "summary": "Avaliação heurística sem LLM",
    }


def normalize_video_review(
    raw: dict,
    *,
    emotion: dict,
    quality_passed: bool,
    render_meta: dict,
    quality_score: int | None = None,
) -> dict:
    data = coerce_dict(raw)
    if not data:
        return _heuristic_review(
            emotion=emotion,
            quality_passed=quality_passed,
            render_meta=render_meta,
            quality_score=quality_score,
        )

    score = _clamp_score(data.get("score"), _clamp_score(emotion.get("overall"), 5))
    min_score = _min_score()
    passed = data.get("passed")
    if not isinstance(passed, bool):
        passed = score >= min_score

    dims_raw = coerce_dict(data.get("dimensions"))
    dimensions = {
        "hook": _clamp_score(dims_raw.get("hook"), score),
        "pacing": _clamp_score(dims_raw.get("pacing"), score),
        "emotion": _clamp_score(dims_raw.get("emotion"), score),
        "cta": _clamp_score(dims_raw.get("cta"), score),
        "technical": _clamp_score(
            dims_raw.get("technical"),
            _technical_dimension(quality_passed=quality_passed, quality_score=quality_score),
        ),
    }

    return {
        "score": score,
        "passed": passed,
        "min_score": min_score,
        "dimensions": dimensions,
        "suggestions": _as_str_list(data.get("suggestions")),
        "summary": str(data.get("summary") or "").strip(),
    }


class VideoReviewAgentHandler(BaseAgentHandler):
    step = "video_review"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        script = coerce_dict(task_input.payload.get("script"))
        emotion = coerce_dict(
            task_input.payload.get("emotion_scores") or task_input.payload.get("emotion")
        )
        quality_passed = bool(task_input.payload.get("quality_passed", True))
        quality_errors = task_input.payload.get("quality_errors") or []
        quality_score = task_input.payload.get("quality_score")
        quality_dimensions = task_input.payload.get("quality_dimensions") or {}
        render = coerce_dict(task_input.payload.get("render_ref"))
        topic = (
            script.get("title")
            or coerce_dict(task_input.payload.get("selected_topic")).get("title")
            or task_input.payload.get("topic", "")
        )
        logs = [f"[video_review] Scoring render for: {topic}"]

        render_meta = {
            "duration_seconds": task_input.payload.get("duration_seconds"),
            "width": task_input.payload.get("width"),
            "height": task_input.payload.get("height"),
            "fps": task_input.payload.get("fps"),
            "has_render": bool(render.get("key")),
        }

        # Enrich with ffprobe when render is available.
        if render.get("key"):
            try:
                am = self.get_asset_manager()
                ffmpeg = FFmpegProvider()
                ref = AssetRef(
                    id=uuid4(),
                    category=AssetCategory.RENDERS,
                    key=render["key"],
                    bucket=render.get("bucket", "contentos"),
                    content_type="video/mp4",
                )
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "review.mp4"
                    path.write_bytes(await am.get(ref))
                    probe = await ffmpeg.probe(path)
                    streams = probe.get("streams", [])
                    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
                    render_meta["duration_seconds"] = float(
                        probe.get("format", {}).get("duration") or render_meta.get("duration_seconds") or 0
                    )
                    if video_stream:
                        render_meta["width"] = int(video_stream.get("width") or 0)
                        render_meta["height"] = int(video_stream.get("height") or 0)
                    logs.append(
                        f"Probe: {render_meta.get('width')}x{render_meta.get('height')} "
                        f"{render_meta.get('duration_seconds'):.1f}s"
                    )
            except Exception as exc:
                logs.append(f"Probe skipped: {exc}")

        quality_json = {
            "quality_passed": quality_passed,
            "quality_errors": quality_errors,
            "quality_score": quality_score,
            "quality_dimensions": quality_dimensions,
        }

        parsed_quality_score: int | None = None
        if quality_score is not None:
            parsed_quality_score = _clamp_score(quality_score, 5)

        try:
            prompt = self.render_prompt(
                "video_review",
                {
                    "topic": topic,
                    "script_json": json.dumps(script, ensure_ascii=False)[:3000],
                    "emotion_json": json.dumps(emotion, ensure_ascii=False)[:1500],
                    "render_json": json.dumps(render_meta, ensure_ascii=False),
                    "quality_json": json.dumps(quality_json, ensure_ascii=False),
                },
                project_id=task_input.project_id,
            )
            logs.append(f"Prompt v{prompt.version}")
            raw, from_cache, cache_key = await self.chat_json_with_cache(
                prompt,
                topic=topic,
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                job_id=task_input.job_id,
            )
            if from_cache:
                logs.append(f"Cache hit ({cache_key})")
            review = normalize_video_review(
                coerce_dict(raw),
                emotion=emotion,
                quality_passed=quality_passed,
                render_meta=render_meta,
                quality_score=parsed_quality_score,
            )
        except Exception as exc:
            logs.append(f"LLM fallback: {exc}")
            review = _heuristic_review(
                emotion=emotion,
                quality_passed=quality_passed,
                render_meta=render_meta,
                quality_score=parsed_quality_score,
            )

        review["min_score"] = _min_score()
        review["render"] = render_meta
        retry_from = os.getenv("CREATIVE_RETRY_FROM", "script").strip() or "script"
        logs.append(
            f"Score={review['score']}/10 passed={review['passed']} "
            f"(min={review['min_score']})"
        )
        if not review["passed"]:
            logs.append(f"Below threshold — engine may retry from '{retry_from}' (B8)")
        if review.get("summary"):
            logs.append(review["summary"])

        ref = await self.get_asset_manager().store(
            AssetCategory.ASSETS,
            json.dumps(review, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="video_review.json",
                content_type="application/json",
            ),
        )

        # Always COMPLETED — Workflow Engine decides creative retry (ADR-006 / B8).
        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "video_review": review,
                "video_score": review["score"],
                "video_review_passed": review["passed"],
                "creative_retry_from": retry_from,
            },
            logs=logs,
        )
