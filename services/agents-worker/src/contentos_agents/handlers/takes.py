"""Takes Manager Agent — matches scenes to video takes via Asset Manager."""

from uuid import UUID

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import JobStatus
from contentos_shared.providers.video_source import MinIOTakeLibraryProvider, VideoClip
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput

try:
    from contentos_sources import get_collection_store
except ImportError:

    def get_collection_store():  # type: ignore[misc]
        return None


class TakesAgentHandler(BaseAgentHandler):
    step = "takes"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        scenes = task_input.payload.get("scenes", [])
        theme = task_input.payload.get("topic") or task_input.payload.get("script", {}).get("title", "general")
        labels = [s.get("label", f"scene_{i}") for i, s in enumerate(scenes)]
        logs = [f"Matching takes for theme: {theme}"]

        clips = self._clips_from_v2_collection(task_input.pipeline_id, labels)
        if clips:
            logs.append(f"Using {len(clips)} V2 collected assets")
        else:
            provider = MinIOTakeLibraryProvider(self.get_asset_manager(), theme)
            clips = await provider.get_clips_for_scenes(theme, labels)
            logs.append(f"Selected {len(clips)} clips from take library")

        clip_data = [{"label": c.label, "asset_key": c.asset_key, "bucket": c.bucket} for c in clips]

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            data={"clips": clip_data, "scenes": scenes},
            logs=logs,
        )

    def _clips_from_v2_collection(self, pipeline_id: UUID, labels: list[str]) -> list[VideoClip]:
        store = get_collection_store()
        if not store:
            return []
        collection = store.get_sync(pipeline_id)
        if not collection or not collection.get("assets"):
            return []
        clips: list[VideoClip] = []
        assets = collection["assets"]
        for i, label in enumerate(labels):
            match = next((a for a in assets if a.get("scene_label") == label), None)
            if not match and i < len(assets):
                match = assets[i]
            if match:
                clips.append(
                    VideoClip(
                        label=label,
                        asset_key=match["asset_key"],
                        bucket=match["bucket"],
                    )
                )
        return clips
