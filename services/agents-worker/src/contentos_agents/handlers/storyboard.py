"""Storyboard AI Agent — visual plan per scene (V3 Tier B4)."""

from __future__ import annotations

import json

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta

FRAMINGS = ("close-up", "medium", "wide")
MOVEMENTS = ("static", "zoom-in", "zoom-out", "pan-left", "pan-right", "ken-burns")
TRANSITIONS = ("cut", "fade", "dissolve")


def _pick(value: str, allowed: tuple[str, ...], default: str) -> str:
    text = str(value or "").lower().strip().replace("_", "-")
    return text if text in allowed else default


def _frames_from_scenes(scenes: list[dict]) -> list[dict]:
    frames: list[dict] = []
    for i, scene in enumerate(scenes):
        start = float(scene.get("start_seconds", i * 5))
        end = float(scene.get("end_seconds", start + 5))
        duration = max(end - start, 1.0)
        label = str(scene.get("label") or f"scene_{i}")
        frames.append(
            {
                "scene_index": i,
                "scene_label": label,
                "framing": "medium" if i % 2 == 0 else "close-up",
                "movement": "ken-burns" if i % 3 == 0 else "static",
                "transition": "cut" if i == 0 else "fade",
                "duration_seconds": duration,
                "visual_notes": str(scene.get("description") or scene.get("visual_hint") or label),
                "b_roll_hint": str(scene.get("visual_hint") or scene.get("description") or ""),
            }
        )
    return frames


def normalize_storyboard(raw: dict, scenes: list[dict]) -> dict:
    data = coerce_dict(raw)
    frames_raw = data.get("frames")
    if not isinstance(frames_raw, list) or not frames_raw:
        return {
            "overall_style": "vertical dinâmico",
            "frames": _frames_from_scenes(scenes),
        }

    frames: list[dict] = []
    for i, item in enumerate(frames_raw):
        frame = coerce_dict(item)
        scene = scenes[i] if i < len(scenes) else {}
        start = float(scene.get("start_seconds", i * 5))
        end = float(scene.get("end_seconds", start + 5))
        default_duration = max(end - start, 1.0)
        try:
            duration = float(frame.get("duration_seconds", default_duration))
        except (TypeError, ValueError):
            duration = default_duration
        frames.append(
            {
                "scene_index": int(frame.get("scene_index", i)),
                "scene_label": str(
                    frame.get("scene_label") or scene.get("label") or f"scene_{i}"
                ),
                "framing": _pick(frame.get("framing", ""), FRAMINGS, "medium"),
                "movement": _pick(frame.get("movement", ""), MOVEMENTS, "static"),
                "transition": _pick(frame.get("transition", ""), TRANSITIONS, "cut"),
                "duration_seconds": max(duration, 1.0),
                "visual_notes": str(frame.get("visual_notes") or scene.get("description") or ""),
                "b_roll_hint": str(frame.get("b_roll_hint") or scene.get("visual_hint") or ""),
            }
        )

    # Ensure one frame per scene
    if scenes and len(frames) < len(scenes):
        frames.extend(_frames_from_scenes(scenes[len(frames) :]))

    return {
        "overall_style": str(data.get("overall_style") or "vertical dinâmico").strip(),
        "frames": frames[: max(len(scenes), 1)],
    }


class StoryboardAgentHandler(BaseAgentHandler):
    step = "storyboard"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        script = coerce_dict(task_input.payload.get("script"))
        scenes = task_input.payload.get("scenes") or []
        if not isinstance(scenes, list):
            scenes = []
        emotion = coerce_dict(
            task_input.payload.get("emotion_scores") or task_input.payload.get("emotion")
        )
        topic = (
            script.get("title")
            or coerce_dict(task_input.payload.get("selected_topic")).get("title")
            or task_input.payload.get("topic", "")
        )
        logs = [f"[storyboard] Planning visuals for {len(scenes)} scenes — {topic}"]

        if not scenes:
            # Derive minimal scenes from script duration
            duration = float(script.get("duration_seconds") or 45)
            scenes = [
                {
                    "label": "main",
                    "start_seconds": 0,
                    "end_seconds": duration,
                    "description": script.get("full_text") or topic,
                    "visual_hint": topic,
                }
            ]
            logs.append("No scenes — using single full-length frame")

        try:
            prompt = self.render_prompt(
                "storyboard",
                {
                    "topic": topic,
                    "script_json": json.dumps(script, ensure_ascii=False)[:3000],
                    "scenes_json": json.dumps(scenes, ensure_ascii=False)[:3000],
                    "emotion_json": json.dumps(emotion, ensure_ascii=False)[:1000],
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
            storyboard = normalize_storyboard(coerce_dict(raw), scenes)
        except Exception as exc:
            logs.append(f"LLM fallback: {exc}")
            storyboard = normalize_storyboard({}, scenes)

        logs.append(
            f"{len(storyboard['frames'])} frames — style={storyboard['overall_style']}"
        )

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(storyboard, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="storyboard.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "storyboard": storyboard,
                "storyboard_frames": storyboard["frames"],
            },
            logs=logs,
        )
