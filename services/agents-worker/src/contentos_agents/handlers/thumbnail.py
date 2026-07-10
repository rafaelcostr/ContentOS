"""Thumbnail Agent — vertical thumbnail via AI Gateway ImageProvider (V2.8 / Phase 10)."""

import json
import os
import time
import uuid

from contentos_agents.handlers._pipeline_base import PipelineAwareHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.providers.image.local_thumbnail import LocalThumbnailProvider
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta
from contentos_shared.thumbnail_qa import validate_thumbnail
from contentos_storage.application.asset_pipeline_service import AssetPipelineService


def _update_video_thumb_sync(pipeline_id, asset_id: uuid.UUID) -> None:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import Video
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            row = session.execute(select(Video).where(Video.pipeline_id == pipeline_id)).scalar_one_or_none()
            if row:
                row.thumb_asset_id = asset_id
                session.commit()
    except Exception:
        pass


def _image_prompt(title: str, topic: str, concept: dict) -> str:
    overlay = concept.get("overlay_text") or title or topic
    style = concept.get("style") or concept.get("mood") or "bold vertical short-form"
    colors = concept.get("colors") or concept.get("palette") or ""
    parts = [str(overlay)]
    if style:
        parts.append(str(style))
    if colors:
        parts.append(str(colors))
    return " | ".join(parts)


class ThumbnailAgentHandler(PipelineAwareHandler):
    step = "thumbnail"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        script = task_input.payload.get("script", {})
        topic = task_input.payload.get("topic") or script.get("title", "")
        title = (task_input.payload.get("publication") or {}).get("title") or script.get("title") or topic
        logs = [f"[thumbnail] Generating for: {title}"]

        concept: dict = {}
        ab_concept = task_input.payload.get("thumbnail_concept")
        if ab_concept:
            concept["overlay_text"] = str(ab_concept)
        try:
            prompt = self.render_prompt(
                "thumbnail",
                {
                    "topic": topic,
                    "title": title,
                    "script_json": json.dumps(script, ensure_ascii=False)[:2000],
                },
                project_id=task_input.project_id,
            )
            logs.append(f"Prompt v{prompt.version}")
            ai = self.get_text_provider()
            concept = await ai.chat_json(prompt.system, prompt.user)
        except Exception as exc:
            logs.append(f"Concept fallback: {exc}")

        image_bytes: bytes | None = None
        image_provider_name = "local"
        render_ref = task_input.payload.get("render_ref")
        started = time.perf_counter()

        # Prefer frame extract when a render exists (richer thumbnails).
        if render_ref:
            try:
                local = LocalThumbnailProvider()
                image_bytes = await local.generate(
                    title=title,
                    topic=topic,
                    render_ref=render_ref,
                    asset_manager=self.get_asset_manager(),
                    concept=concept,
                )
                image_provider_name = "ffmpeg"
                logs.append("Generated from render frame")
            except Exception as exc:
                logs.append(f"Frame extract fallback: {exc}")
                image_bytes = None

        # Phase 10: ImageProvider via AI Gateway (local Pillow adapter by default).
        if not image_bytes:
            try:
                from contentos_ai_client.providers import GatewayImageProvider

                image = GatewayImageProvider(provider_key="local", agent=self.step)
                image_bytes = await image.generate_image(
                    _image_prompt(title, topic, concept),
                    size="1080x1920",
                )
                image_provider_name = getattr(image, "provider_key", None) or "local"
                logs.append(f"Generated via AI Gateway ImageProvider ({len(image_bytes)} bytes)")
            except Exception as exc:
                logs.append(f"Gateway image fallback: {exc}")
                local = LocalThumbnailProvider()
                image_bytes = await local.generate(
                    title=title,
                    topic=topic,
                    render_ref=None,
                    asset_manager=None,
                    concept=concept,
                )
                image_provider_name = "local"
                logs.append(f"Generated local placeholder ({len(image_bytes)} bytes)")

        duration_ms = int((time.perf_counter() - started) * 1000)
        self._record_image_cost(
            task_input,
            image_bytes=len(image_bytes or b""),
            duration_ms=duration_ms,
            provider=image_provider_name,
            model="thumbnail",
        )
        logs.append(f"Cost tracked ({duration_ms}ms)")

        thumb_qa = validate_thumbnail(image_bytes or b"")
        asset_manager = self.get_asset_manager()
        persisted = await AssetPipelineService(asset_manager).store_and_persist(
            AssetCategory.THUMBS,
            image_bytes,
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="thumbnail.jpg",
                content_type="image/jpeg",
            ),
            extra_tags=["thumbnail", f"pipeline:{task_input.pipeline_id}"],
            metadata={
                "topic": topic,
                "title": title,
                "provider": image_provider_name,
                "width": thumb_qa.width,
                "height": thumb_qa.height,
            },
        )
        ref = persisted.ref
        if thumb_qa.passed:
            logs.append(f"Thumbnail QA passed ({thumb_qa.width}x{thumb_qa.height})")
        else:
            logs.append("Thumbnail QA warnings: " + "; ".join(thumb_qa.errors))
        _update_video_thumb_sync(task_input.pipeline_id, ref.id)
        logs.append(f"Stored thumb {ref.key}")

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "thumb_ref": {"id": str(ref.id), "key": ref.key, "bucket": ref.bucket},
                "concept": concept,
                **thumb_qa.to_dict(),
            },
            logs=logs,
        )
