"""Scene Director Agent — storyboard → FFmpeg render plan (V3 Tier B5)."""

from __future__ import annotations

import json

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.director_plan import build_director_plan
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta


class SceneDirectorAgentHandler(BaseAgentHandler):
    step = "scene_director"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        storyboard = coerce_dict(task_input.payload.get("storyboard"))
        scenes = task_input.payload.get("scenes") or []
        if not isinstance(scenes, list):
            scenes = []
        emotion = coerce_dict(
            task_input.payload.get("emotion_scores") or task_input.payload.get("emotion")
        )
        script = coerce_dict(task_input.payload.get("script"))
        topic = (
            script.get("title")
            or coerce_dict(task_input.payload.get("selected_topic")).get("title")
            or task_input.payload.get("topic", "")
        )

        frames = storyboard.get("frames") or task_input.payload.get("storyboard_frames") or []
        if not storyboard and isinstance(frames, list) and frames:
            storyboard = {"frames": frames, "overall_style": "vertical dinâmico"}

        logs = [f"[scene_director] Building render plan for {len(scenes) or len(frames)} scenes — {topic}"]

        if not storyboard.get("frames") and not scenes:
            duration = float(script.get("duration_seconds") or 45)
            scenes = [
                {
                    "label": "main",
                    "start_seconds": 0,
                    "end_seconds": duration,
                    "description": script.get("full_text") or topic,
                }
            ]
            logs.append("No storyboard — using scene/script fallback")

        director_plan = build_director_plan(
            storyboard=storyboard,
            scenes=scenes,
            emotion=emotion,
        )
        logs.append(
            f"Plan pacing={director_plan['pacing']} energy={director_plan['energy']} "
            f"segments={len(director_plan['segments'])}"
        )

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(director_plan, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="director_plan.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "director_plan": director_plan,
                "director_segments": director_plan["segments"],
                "render_pacing": director_plan["pacing"],
            },
            logs=logs,
        )
