"""Workflow Engine — central orchestrator. Agents NEVER talk to each other."""

import os
from datetime import datetime, timezone
from uuid import UUID

from contentos_database.models import DeadLetterJob, Job, LogEntry, Pipeline, Project, WorkflowDefinition
from contentos_shared.enums import JobStatus, PipelineStatus, PipelineStep
from contentos_shared.events import WorkflowEvent
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.workflow_templates import get_builtin, get_default_workflow_name
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

MAX_RETRIES = 3
RETRY_DELAYS = [30, 60, 120]


def _max_creative_retries() -> int:
    try:
        return max(0, int(os.getenv("MAX_CREATIVE_RETRIES", "1")))
    except ValueError:
        return 1


def _creative_retry_from() -> str:
    return os.getenv("CREATIVE_RETRY_FROM", "script").strip() or "script"


def _max_director_retries() -> int:
    try:
        return max(0, int(os.getenv("MAX_DIRECTOR_RETRIES", "1")))
    except ValueError:
        return 1


def _retention_retry_enabled() -> bool:
    return os.getenv("RETENTION_RETRY_ENABLED", "true").lower() in ("1", "true", "yes")


def _ai_director_enabled() -> bool:
    return os.getenv("AI_DIRECTOR_ENABLED", "true").lower() in ("1", "true", "yes")


def _pipeline_retry_passed(output_data: dict, *, retention_only: bool = False) -> bool:
    """Combine video_review + retention gates for creative retry (V5.2.2)."""
    if retention_only:
        if "retention_passed" not in output_data:
            return True
        return bool(output_data.get("retention_passed"))
    passed = bool(output_data.get("video_review_passed", True))
    if _retention_retry_enabled() and "retention_passed" in output_data:
        passed = passed and bool(output_data.get("retention_passed"))
    return passed


def should_creative_retry(*, passed: bool, retry_count: int, max_retries: int) -> str:
    """Return 'retry', 'advance', or 'advance_exhausted' (ADR-006)."""
    if passed:
        return "advance"
    if retry_count < max_retries:
        return "retry"
    return "advance_exhausted"

STEP_QUEUE_MAP: dict[str, str] = {
    "trend_intelligence": "contentos.trend_intelligence",
    "research": "contentos.research",
    "hook": "contentos.hook",
    "script": "contentos.script",
    "script_review": "contentos.script_review",
    "emotion": "contentos.emotion",
    "content_score": "contentos.content_score",
    "content_intelligence": "contentos.content_intelligence",
    "scene": "contentos.scene",
    "storyboard": "contentos.storyboard",
    "scene_director": "contentos.scene_director",
    "takes": "contentos.takes",
    "voice": "contentos.voice",
    "subtitle": "contentos.subtitle",
    "editor": "contentos.editor",
    "retention": "contentos.retention",
    "seo": "contentos.seo",
    "ai_director": "contentos.ai_director",
    "creative_memory": "contentos.creative_memory",
    "quality": "contentos.quality",
    "video_review": "contentos.video_review",
    "auto_retry": "contentos.auto_retry",
    "publisher": "contentos.publisher",
    "multi_content": "contentos.multi_content",
    "multi_content_video": "contentos.multi_content_video",
    "clip_research": "contentos.clip_research",
    "asset_collector": "contentos.asset_collector",
    "asset_index": "contentos.asset_index",
    "media_analyze": "contentos.media_analyze",
    "asset_search": "contentos.asset_search",
    "thumbnail": "contentos.thumbnail",
    "analytics": "contentos.analytics",
    "learning": "contentos.learning",
    "knowledge_base": "contentos.knowledge_base",
}


class WorkflowEngine:
    """Orchestrates pipeline execution via Celery queues."""

    def __init__(self, session: AsyncSession, event_publisher: object | None = None) -> None:
        self.session = session
        self.events = event_publisher

    async def create_pipeline(
        self,
        project_id: UUID,
        topic: str,
        workflow_name: str | None = None,
        *,
        context_json: dict | None = None,
    ) -> Pipeline:
        resolved_name = workflow_name or get_default_workflow_name()
        steps, _ = await self._load_workflow(resolved_name)
        project = await self.session.get(Project, project_id)
        pipeline = Pipeline(
            project_id=project_id,
            org_id=project.org_id if project else None,
            topic=topic,
            workflow_name=resolved_name,
            status=PipelineStatus.PENDING,
            context_json=context_json or None,
        )
        self.session.add(pipeline)
        await self.session.flush()

        for i, step in enumerate(steps):
            job = Job(
                pipeline_id=pipeline.id,
                step=step,
                order=i,
                status=JobStatus.PENDING,
                max_retries=MAX_RETRIES,
            )
            self.session.add(job)

        await self.session.flush()
        await self._emit(WorkflowEvent(type="pipeline.created", pipeline_id=pipeline.id, status="pending"))
        return pipeline

    async def start_pipeline(self, pipeline_id: UUID) -> None:
        pipeline = await self._get_pipeline(pipeline_id)
        if pipeline.status == PipelineStatus.CANCELLED:
            return
        pipeline.status = PipelineStatus.RUNNING
        steps = await self._ordered_job_steps(pipeline)
        if steps:
            await self._enqueue_step(pipeline, steps[0])

    async def cancel_pipeline(self, pipeline_id: UUID) -> Pipeline:
        """Stop a running pipeline and revoke pending Celery tasks."""
        pipeline = await self._get_pipeline(pipeline_id)
        if pipeline.status in (PipelineStatus.COMPLETED, PipelineStatus.CANCELLED):
            return pipeline

        for job in pipeline.jobs:
            if job.status in (JobStatus.PENDING, JobStatus.RUNNING, JobStatus.RETRYING):
                if job.celery_task_id:
                    try:
                        from contentos_workflow.tasks import celery_app

                        celery_app.control.revoke(job.celery_task_id, terminate=True, signal="SIGTERM")
                    except Exception:
                        pass
                job.status = JobStatus.CANCELLED
                if not job.finished_at:
                    job.finished_at = datetime.now(timezone.utc)

        pipeline.status = PipelineStatus.CANCELLED
        pipeline.current_step = None
        await self._emit(
            WorkflowEvent(type="pipeline.cancelled", pipeline_id=pipeline.id, status="cancelled")
        )
        await self.session.flush()
        return pipeline

    async def handle_agent_callback(
        self,
        job_id: UUID,
        status: JobStatus,
        output_data: dict | None = None,
        error: str | None = None,
        logs: list[str] | None = None,
    ) -> None:
        job = await self._get_job(job_id)
        pipeline = await self._get_pipeline(job.pipeline_id)

        if pipeline.status == PipelineStatus.CANCELLED:
            return

        job.status = status
        job.output_data = output_data
        job.error_message = error
        job.finished_at = datetime.now(timezone.utc)

        if logs:
            for msg in logs:
                self.session.add(
                    LogEntry(
                        job_id=job.id,
                        pipeline_id=pipeline.id,
                        agent=job.step,
                        message=msg,
                    )
                )

        if status == JobStatus.COMPLETED:
            await self._emit(
                WorkflowEvent(
                    type="step.completed", pipeline_id=pipeline.id, job_id=job.id, step=job.step, status="completed"
                )
            )
            if job.step == "scene" and not await self._pipeline_has_step(pipeline, "clip_research"):
                await self._dispatch_clip_pipeline(pipeline)
            if job.step == "publisher" and output_data:
                await self._create_video_record(pipeline, output_data)
            if (
                job.step == "retention"
                and not await self._pipeline_has_step(pipeline, "auto_retry")
                and await self._maybe_creative_retry(
                    pipeline, job, output_data or {}, retention_only=True
                )
            ):
                await self.session.flush()
                return
            if (
                job.step == "video_review"
                and not await self._pipeline_has_step(pipeline, "auto_retry")
                and await self._maybe_creative_retry(pipeline, job, output_data or {})
            ):
                await self.session.flush()
                return
            if job.step == "auto_retry" and await self._maybe_creative_retry(pipeline, job, output_data or {}):
                await self.session.flush()
                return
            if (
                job.step == "ai_director"
                and _ai_director_enabled()
                and await self._maybe_director_retry(pipeline, job, output_data or {})
            ):
                await self.session.flush()
                return
            await self.session.flush()
            await self._advance_pipeline(pipeline)
        elif status == JobStatus.FAILED:
            if job.step == "quality" and output_data and output_data.get("retry_step"):
                retry_step = output_data["retry_step"]
                job.status = JobStatus.PENDING
                job.retry_count += 1
                await self.retry_step(pipeline.id, retry_step)
            else:
                await self._handle_failure(job, pipeline, error or "Unknown error")

        await self.session.flush()

    async def _create_video_record(self, pipeline: Pipeline, output_data: dict) -> None:
        from contentos_database.models import Video

        pub = output_data.get("publication", {})
        payload = await self._build_payload(pipeline, "publisher")
        render_ref = payload.get("render_ref") or {}
        thumb_ref = payload.get("thumb_ref") or {}
        duration = payload.get("duration_seconds")
        width = int(payload.get("width") or 1080)
        height = int(payload.get("height") or 1920)
        fps = int(payload.get("fps") or 60)

        def asset_id_from(ref: dict) -> UUID | None:
            try:
                return UUID(str(ref.get("id"))) if ref.get("id") else None
            except (TypeError, ValueError):
                return None

        video = Video(
            project_id=pipeline.project_id,
            pipeline_id=pipeline.id,
            title=pub.get("title", pipeline.topic),
            description=pub.get("description"),
            status=pub.get("status", "ready"),
            hashtags=pub.get("hashtags"),
            width=width,
            height=height,
            fps=fps,
            duration_seconds=duration,
            render_asset_id=asset_id_from(render_ref),
            thumb_asset_id=asset_id_from(thumb_ref),
        )
        platforms = pub.get("platforms") or output_data.get("platform_publications")
        if platforms:
            video.description = (video.description or "") + f"\n[platforms: {', '.join(platforms.keys())}]"
        variants = output_data.get("video_variants") or output_data.get("video_variants_report")
        if isinstance(variants, dict):
            by_platform = variants.get("by_platform")
            if by_platform:
                video.platform_variants = by_platform
        self.session.add(video)

    async def _advance_pipeline(self, pipeline: Pipeline) -> None:
        if pipeline.status == PipelineStatus.CANCELLED:
            return
        await self.session.refresh(pipeline, ["jobs"])
        completed_steps = {j.step for j in pipeline.jobs if j.status == JobStatus.COMPLETED}
        for step in await self._ordered_job_steps(pipeline):
            if step not in completed_steps:
                await self._enqueue_step(pipeline, step)
                return

        pipeline.status = PipelineStatus.COMPLETED
        pipeline.current_step = None
        await self._emit(WorkflowEvent(type="pipeline.completed", pipeline_id=pipeline.id, status="completed"))
        await self._dispatch_v2_async_agents(pipeline)

    async def _ordered_job_steps(self, pipeline: Pipeline) -> list[str]:
        await self.session.refresh(pipeline, ["jobs"])
        return [j.step for j in sorted(pipeline.jobs, key=lambda j: j.order)]

    async def _pipeline_has_step(self, pipeline: Pipeline, step: str) -> bool:
        await self.session.refresh(pipeline, ["jobs"])
        return any(j.step == step for j in pipeline.jobs)

    async def _load_workflow(self, name: str) -> tuple[list[str], dict]:
        result = await self.session.execute(select(WorkflowDefinition).where(WorkflowDefinition.name == name))
        wf = result.scalar_one_or_none()
        if wf:
            return list(wf.steps), dict(wf.config or {})

        builtin = get_builtin(name)
        if builtin:
            return list(builtin["steps"]), dict(builtin.get("config") or {})

        default_name = get_default_workflow_name()
        if name != default_name:
            return await self._load_workflow(default_name)
        return [step.value for step in PipelineStep.ordered()], {}

    async def _workflow_config(self, pipeline: Pipeline) -> dict:
        name = pipeline.workflow_name or get_default_workflow_name()
        _, cfg = await self._load_workflow(name)
        return cfg

    def _env_enabled(self, env_var: str, default: str = "false") -> bool:
        return os.getenv(env_var, default).lower() in ("true", "1", "yes")

    async def _is_clip_pipeline_enabled(self, pipeline: Pipeline) -> bool:
        cfg = await self._workflow_config(pipeline)
        if "enable_clip_pipeline" in cfg:
            return bool(cfg["enable_clip_pipeline"])
        return self._env_enabled("ENABLE_V2_CLIP_PIPELINE")

    async def _is_thumbnail_enabled(self, pipeline: Pipeline) -> bool:
        cfg = await self._workflow_config(pipeline)
        if "enable_thumbnail" in cfg:
            return bool(cfg["enable_thumbnail"])
        return self._env_enabled("ENABLE_THUMBNAIL")

    async def _is_analytics_enabled(self, pipeline: Pipeline) -> bool:
        cfg = await self._workflow_config(pipeline)
        if "enable_analytics_ai" in cfg:
            return bool(cfg["enable_analytics_ai"])
        return self._env_enabled("ENABLE_ANALYTICS_AI", default="true")

    async def _is_learning_enabled(self, pipeline: Pipeline) -> bool:
        cfg = await self._workflow_config(pipeline)
        if "enable_learning" in cfg:
            return bool(cfg["enable_learning"])
        return self._env_enabled("LEARNING_ENGINE_ENABLED", default="true")

    async def _dispatch_clip_pipeline(self, pipeline: Pipeline) -> None:
        """Optional V2 clip research chain after scene (non-blocking)."""
        if not await self._is_clip_pipeline_enabled(pipeline):
            return
        from contentos_workflow.tasks import dispatch_async_agent

        payload = await self._build_full_payload(pipeline)
        dispatch_async_agent("clip_research", str(pipeline.id), str(pipeline.project_id), payload)

    async def _dispatch_v2_async_agents(self, pipeline: Pipeline) -> None:
        """Enqueue optional V2 async agents after main pipeline completes (non-blocking)."""
        from contentos_workflow.tasks import dispatch_async_agent

        payload = await self._build_full_payload(pipeline)
        pid = str(pipeline.id)
        proj = str(pipeline.project_id)

        if await self._is_thumbnail_enabled(pipeline) and not await self._pipeline_has_step(pipeline, "thumbnail"):
            dispatch_async_agent("thumbnail", pid, proj, payload)

        if await self._is_analytics_enabled(pipeline) and not await self._pipeline_has_step(pipeline, "analytics"):
            dispatch_async_agent("analytics", pid, proj, payload)

        if await self._is_learning_enabled(pipeline) and not await self._pipeline_has_step(pipeline, "learning"):
            dispatch_async_agent("learning", pid, proj, payload)

    async def _build_full_payload(self, pipeline: Pipeline) -> dict:
        await self.session.refresh(pipeline, ["jobs"])
        payload: dict = {"topic": pipeline.topic}
        for job in sorted(pipeline.jobs, key=lambda j: j.order):
            if job.output_data and job.status == JobStatus.COMPLETED:
                payload.update(job.output_data)
        return payload

    async def _enqueue_step(self, pipeline: Pipeline, step: str) -> None:
        result = await self.session.execute(select(Job).where(Job.pipeline_id == pipeline.id, Job.step == step))
        job = result.scalar_one()
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        pipeline.current_step = step

        from contentos_workflow.tasks import dispatch_agent_task

        queue = STEP_QUEUE_MAP.get(step)
        if not queue:
            raise ValueError(f"Unknown pipeline step: {step}")

        task_id = dispatch_agent_task(
            queue=queue,
            job_id=str(job.id),
            pipeline_id=str(pipeline.id),
            project_id=str(pipeline.project_id),
            step=step,
            payload=await self._build_payload(pipeline, step),
        )
        job.celery_task_id = task_id

        await self._emit(
            WorkflowEvent(
                type="step.started", pipeline_id=pipeline.id, job_id=job.id, step=step, status="running"
            )
        )

    async def _handle_failure(self, job: Job, pipeline: Pipeline, error: str) -> None:
        if job.retry_count < job.max_retries:
            job.retry_count += 1
            job.status = JobStatus.RETRYING
            pipeline.status = PipelineStatus.RUNNING
            delay = RETRY_DELAYS[min(job.retry_count - 1, len(RETRY_DELAYS) - 1)]

            from contentos_workflow.tasks import dispatch_agent_task

            queue = STEP_QUEUE_MAP.get(job.step, f"contentos.{job.step}")
            dispatch_agent_task(
                queue=queue,
                job_id=str(job.id),
                pipeline_id=str(pipeline.id),
                project_id=str(pipeline.project_id),
                step=job.step,
                payload=await self._build_payload(pipeline, job.step),
                countdown=delay,
            )
            await self._emit(
                WorkflowEvent(
                    type="step.retrying",
                    pipeline_id=pipeline.id,
                    job_id=job.id,
                    step=job.step,
                    status="retrying",
                    data={"retry": job.retry_count, "delay": delay},
                )
            )
        else:
            job.status = JobStatus.FAILED
            pipeline.status = PipelineStatus.FAILED
            pipeline.error_message = error
            self.session.add(
                DeadLetterJob(
                    job_id=job.id,
                    pipeline_id=pipeline.id,
                    step=job.step,
                    error_message=error,
                    payload=job.input_data,
                )
            )
            await self._emit(
                WorkflowEvent(
                    type="step.dlq",
                    pipeline_id=pipeline.id,
                    job_id=job.id,
                    step=job.step,
                    status="failed",
                )
            )

    async def retry_step(self, pipeline_id: UUID, step: str) -> None:
        """Quality agent can trigger re-run of a specific step."""
        pipeline = await self._get_pipeline(pipeline_id)
        result = await self.session.execute(select(Job).where(Job.pipeline_id == pipeline_id, Job.step == step))
        job = result.scalar_one()
        job.status = JobStatus.PENDING
        job.retry_count = 0
        job.error_message = None
        await self._enqueue_step(pipeline, step)

    async def _maybe_creative_retry(
        self,
        pipeline: Pipeline,
        job: Job,
        output_data: dict,
        *,
        retention_only: bool = False,
    ) -> bool:
        """Rewind pipeline when creative quality score is low (Tier B8 / ADR-006).

        Returns True if a creative retry was started (caller must not advance).
        """
        passed = _pipeline_retry_passed(output_data, retention_only=retention_only)
        decision = should_creative_retry(
            passed=passed,
            retry_count=pipeline.retry_count,
            max_retries=_max_creative_retries(),
        )
        score = output_data.get("video_score")
        retention_score = output_data.get("retention_score")
        min_score = (output_data.get("video_review") or {}).get("min_score")
        retry_target = output_data.get("retention_retry_target")

        if decision == "advance":
            return False

        if decision == "advance_exhausted":
            note = (
                f"Creative retry budget exhausted "
                f"({pipeline.retry_count}/{_max_creative_retries()}); "
                f"score={score} retention={retention_score} min={min_score} — continuing pipeline"
            )
            job.output_data = {
                **output_data,
                "creative_retry_exhausted": True,
                "creative_retry_note": note,
            }
            self.session.add(
                LogEntry(
                    job_id=job.id,
                    pipeline_id=pipeline.id,
                    agent=job.step,
                    message=note,
                )
            )
            await self._emit(
                WorkflowEvent(
                    type="creative_retry.exhausted",
                    pipeline_id=pipeline.id,
                    job_id=job.id,
                    step=job.step,
                    status="completed",
                    data={"score": score, "attempts": pipeline.retry_count},
                )
            )
            return False

        # decision == "retry"
        steps = await self._ordered_job_steps(pipeline)
        retry_from = output_data.get("creative_retry_from") or _creative_retry_from()
        if retry_from not in steps:
            retry_from = "script" if "script" in steps else steps[0]

        pipeline.retry_count += 1
        await self._rewind_from_step(pipeline, retry_from)
        note = (
            f"Creative retry {pipeline.retry_count}/{_max_creative_retries()} "
            f"from '{retry_from}'"
            + (f" target={retry_target}" if retry_target else "")
            + f" (passed={passed} score={score} retention={retention_score} min={min_score})"
        )
        self.session.add(
                LogEntry(
                    job_id=job.id,
                    pipeline_id=pipeline.id,
                    agent=job.step,
                    message=note,
                )
        )
        await self._emit(
            WorkflowEvent(
                type="creative_retry.started",
                pipeline_id=pipeline.id,
                job_id=job.id,
                step=job.step,
                status="retrying",
                data={
                    "attempt": pipeline.retry_count,
                    "from_step": retry_from,
                    "score": score,
                    "retention_score": retention_score,
                    "retention_retry_target": retry_target,
                    "min_score": min_score,
                },
            )
        )
        await self._enqueue_step(pipeline, retry_from)
        return True

    async def _maybe_director_retry(self, pipeline: Pipeline, job: Job, output_data: dict) -> bool:
        """Partial pipeline rewind when AI Director score is below threshold (V5.2.4)."""
        if output_data.get("director_passed", True):
            return False

        retry_count = int(output_data.get("director_retry_count") or 0)
        max_retries = _max_director_retries()
        overall = output_data.get("director_overall_score")
        target = output_data.get("director_retry_target")
        decision = coerce_dict(output_data.get("director_decision"))

        if retry_count >= max_retries:
            note = (
                f"AI Director retry budget exhausted ({retry_count}/{max_retries}); "
                f"score={overall} — continuing pipeline"
            )
            job.output_data = {**output_data, "director_retry_exhausted": True, "director_retry_note": note}
            self.session.add(
                LogEntry(job_id=job.id, pipeline_id=pipeline.id, agent=job.step, message=note)
            )
            await self._emit(
                WorkflowEvent(
                    type="director_retry.exhausted",
                    pipeline_id=pipeline.id,
                    job_id=job.id,
                    step=job.step,
                    status="completed",
                    data={"score": overall, "attempts": retry_count},
                )
            )
            return False

        steps = await self._ordered_job_steps(pipeline)
        retry_from = output_data.get("creative_retry_from") or decision.get("retry_from") or _creative_retry_from()
        if retry_from not in steps:
            retry_from = "script" if "script" in steps else steps[0]

        next_count = retry_count + 1
        await self._stash_director_retry_count(pipeline, retry_from, next_count)
        await self._rewind_from_step(pipeline, retry_from)
        job.output_data = {**output_data, "director_retry_count": next_count}
        note = (
            f"AI Director retry {next_count}/{max_retries} from '{retry_from}'"
            + (f" target={target}" if target else "")
            + f" score={overall} — {decision.get('reason', '')}"
        )
        self.session.add(
            LogEntry(job_id=job.id, pipeline_id=pipeline.id, agent=job.step, message=note)
        )
        await self._emit(
            WorkflowEvent(
                type="director_retry.started",
                pipeline_id=pipeline.id,
                job_id=job.id,
                step=job.step,
                status="retrying",
                data={
                    "attempt": next_count,
                    "from_step": retry_from,
                    "target": target,
                    "score": overall,
                },
            )
        )
        await self._enqueue_step(pipeline, retry_from)
        return True

    async def _stash_director_retry_count(self, pipeline: Pipeline, from_step: str, count: int) -> None:
        """Persist director retry counter on a completed job that survives rewind."""
        await self.session.refresh(pipeline, ["jobs"])
        start_order = next((j.order for j in pipeline.jobs if j.step == from_step), 0)
        for job in sorted(pipeline.jobs, key=lambda j: j.order, reverse=True):
            if job.order >= start_order:
                continue
            if job.status != JobStatus.COMPLETED:
                continue
            data = dict(job.output_data or {})
            data["director_retry_count"] = count
            job.output_data = data
            return

    async def _rewind_from_step(self, pipeline: Pipeline, from_step: str) -> None:
        """Reset jobs from from_step through the end so payload rebuilds cleanly."""
        await self.session.refresh(pipeline, ["jobs"])
        start_order = next((j.order for j in pipeline.jobs if j.step == from_step), None)
        if start_order is None:
            return
        for job in pipeline.jobs:
            if job.order < start_order:
                continue
            job.status = JobStatus.PENDING
            job.output_data = None
            job.input_data = None
            job.error_message = None
            job.celery_task_id = None
            job.started_at = None
            job.finished_at = None
            job.retry_count = 0
        pipeline.status = PipelineStatus.RUNNING
        pipeline.current_step = from_step
        pipeline.error_message = None

    async def _merge_pipeline_context(self, payload: dict, pipeline: Pipeline) -> dict:
        if pipeline.context_json:
            payload.update(pipeline.context_json)
        return payload

    async def _build_payload(self, pipeline: Pipeline, current_step: str) -> dict:
        await self.session.refresh(pipeline, ["jobs"])
        payload: dict = {"topic": pipeline.topic}
        for job in sorted(pipeline.jobs, key=lambda j: j.order):
            if job.step == current_step:
                break
            if job.output_data and job.status == JobStatus.COMPLETED:
                payload.update(job.output_data)
        payload = await self._inject_project_voice_profile(payload, pipeline.project_id)
        payload = await self._inject_project_dna_hints(payload, pipeline.project_id)
        return await self._merge_pipeline_context(payload, pipeline)

    async def _inject_project_dna_hints(self, payload: dict, project_id: UUID) -> dict:
        try:
            from contentos_shared.dna.pipeline_hints import project_dna_payload_hints_async

            hints = await project_dna_payload_hints_async(self.session, project_id)
            for key, value in hints.items():
                if not payload.get(key):
                    payload[key] = value
        except Exception:
            pass
        return payload

    async def _inject_project_voice_profile(self, payload: dict, project_id: UUID) -> dict:
        if payload.get("voice_profile") or payload.get("voice_profile_id") or payload.get("voice_profile_name"):
            return payload
        try:
            from contentos_shared.voice.project_library import project_voice_payload_hints

            hints = await project_voice_payload_hints(self.session, project_id)
            if hints:
                payload.update(hints)
        except Exception:
            pass
        return payload

    async def _get_pipeline(self, pipeline_id: UUID) -> Pipeline:
        result = await self.session.execute(
            select(Pipeline).options(selectinload(Pipeline.jobs)).where(Pipeline.id == pipeline_id)
        )
        pipeline = result.scalar_one_or_none()
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        return pipeline

    async def _get_job(self, job_id: UUID) -> Job:
        result = await self.session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        return job

    async def _emit(self, event: WorkflowEvent) -> None:
        if self.events:
            await self.events.publish(event)
