"""Base handler for all agents — Template Method pattern."""

import asyncio
import os
from abc import ABC, abstractmethod
from uuid import UUID

from contentos_shared.enums import JobStatus
from contentos_shared.providers.factory import get_provider_factory
from contentos_shared.providers.protocols import SpeechProvider, SubtitleProvider, TextProvider
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_storage.factory import StorageSettings, get_asset_manager

try:
    from contentos_cache import get_cache_service
except ImportError:

    def get_cache_service():  # type: ignore[misc]
        return None


try:
    from contentos_cost import get_cost_tracker
except ImportError:

    def get_cost_tracker():  # type: ignore[misc]
        return None


try:
    from contentos_memory import get_memory_service
except ImportError:

    def get_memory_service():  # type: ignore[misc]
        return None


try:
    from contentos_growth.application.channel_memory_service import get_channel_memory_service
except ImportError:

    def get_channel_memory_service():  # type: ignore[misc]
        return None


try:
    from contentos_models import get_model_manager
except ImportError:

    def get_model_manager():  # type: ignore[misc]
        return None


try:
    from contentos_prompts import PromptService, RenderedPrompt, get_prompt_service
except ImportError:
    PromptService = None  # type: ignore[misc, assignment]
    RenderedPrompt = None  # type: ignore[misc, assignment]

    def get_prompt_service():  # type: ignore[misc]
        raise RuntimeError("contentos-prompts package not installed")


try:
    from contentos_events import DomainEvent, get_event_bus
except ImportError:
    DomainEvent = None  # type: ignore[misc, assignment]

    def get_event_bus():  # type: ignore[misc]
        return None


class BaseAgentHandler(ABC):
    step: str = "base"

    @abstractmethod
    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        """Agent-specific logic."""

    async def run(self, **kwargs) -> dict:
        from contentos_shared.telemetry import extract_context, start_span

        trace_carrier = kwargs.pop("_trace_carrier", None)
        parent_ctx = extract_context(trace_carrier) if trace_carrier else None

        task_input = AgentTaskInput(
            job_id=UUID(str(kwargs["job_id"])),
            pipeline_id=UUID(str(kwargs["pipeline_id"])),
            project_id=UUID(str(kwargs["project_id"])),
            step=kwargs["step"],
            payload=kwargs.get("payload", {}),
        )
        self._last_task_input = task_input
        logs = [f"[{self.step}] Starting job {task_input.job_id}"]
        span_attrs = {
            "contentos.step": self.step,
            "contentos.job_id": str(task_input.job_id),
            "contentos.pipeline_id": str(task_input.pipeline_id),
            "contentos.project_id": str(task_input.project_id),
        }
        try:
            with start_span(f"agent.{self.step}.execute", span_attrs, context=parent_ctx):
                result = await self.execute(task_input)
                result.logs = logs + result.logs
                await self._callback(result)
                return {"status": result.status, "job_id": str(result.job_id)}
        except Exception as exc:
            output = AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.FAILED.value,
                logs=logs + [f"Error: {exc}"],
                error=str(exc),
            )
            await self._callback(output)
            raise

    async def _callback(self, output: AgentTaskOutput) -> None:
        import httpx

        workflow_url = os.getenv("WORKFLOW_CALLBACK_URL", "http://workflow-engine:8001/internal/callback")
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                workflow_url,
                json={
                    "job_id": str(output.job_id),
                    "status": output.status,
                    "output_data": output.data,
                    "artifacts": [
                        {"id": str(a.id), "category": a.category.value, "key": a.key, "bucket": a.bucket}
                        for a in output.artifacts
                    ],
                    "logs": output.logs,
                    "error": output.error,
                },
            )

        try:
            bus = get_event_bus()
            if bus and DomainEvent and hasattr(self, "_last_task_input") and self._last_task_input:
                ti = self._last_task_input
                event = DomainEvent.from_agent_callback(
                    step=self.step,
                    project_id=ti.project_id,
                    pipeline_id=ti.pipeline_id,
                    job_id=output.job_id,
                    status=output.status,
                    payload={"error": output.error} if output.error else {},
                )
                bus.publish_sync(event)
        except Exception:
            pass

    def get_asset_manager(self):
        return get_asset_manager(
            StorageSettings(
                endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
                access_key=os.getenv("MINIO_ACCESS_KEY", "contentos"),
                secret_key=os.getenv("MINIO_SECRET_KEY", "contentos_secret"),
                bucket=os.getenv("MINIO_BUCKET", "contentos"),
                secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
            )
        )

    def get_text_provider(self) -> TextProvider:
        from contentos_shared.providers.builder import build_text_provider

        manager = get_model_manager()
        if manager:
            cfg = manager.get_config(self.step)
            if cfg.provider_type == "text":
                return build_text_provider(cfg.provider, cfg.model, agent=self.step)
        factory = get_provider_factory()
        status = factory.status()
        return build_text_provider(status["text"], agent=self.step)

    def get_speech_provider(self) -> SpeechProvider:
        from contentos_shared.providers.builder import build_speech_provider

        manager = get_model_manager()
        if manager:
            cfg = manager.get_config(self.step)
            if cfg.provider_type == "speech":
                return build_speech_provider(cfg.provider, cfg.model, agent=self.step)
        factory = get_provider_factory()
        status = factory.status()
        return build_speech_provider(status["speech"], agent=self.step)

    def get_subtitle_provider(self) -> SubtitleProvider:
        from contentos_shared.providers.builder import build_subtitle_provider

        manager = get_model_manager()
        if manager:
            cfg = manager.get_config(self.step)
            if cfg.provider_type == "subtitle":
                return build_subtitle_provider(cfg.provider, cfg.model, agent=self.step)
        factory = get_provider_factory()
        status = factory.status()
        return build_subtitle_provider(status["subtitle"], agent=self.step)

    def get_prompt_service(self) -> PromptService:
        return get_prompt_service()

    def render_prompt(
        self,
        prompt_id: str,
        variables: dict[str, str] | None = None,
        *,
        project_id: UUID | None = None,
    ) -> RenderedPrompt:
        service = get_prompt_service()
        service.reload()
        vars_map = {k: str(v) for k, v in (variables or {}).items()}

        memory_svc = get_memory_service()
        if memory_svc and project_id:
            memory_vars = memory_svc.prompt_variables(project_id)
            for key in (
                "memory_context",
                "dna_context",
                "brand_context",
                "niche",
                "narrator_persona",
                "pace",
                "cta_style",
                "mission",
                "target_audience",
                "specialist_context",
                "specialist_id",
            ):
                if not vars_map.get(key) and memory_vars.get(key):
                    vars_map[key] = memory_vars[key]
        else:
            if not vars_map.get("memory_context"):
                vars_map["memory_context"] = ""
            if not vars_map.get("dna_context"):
                vars_map["dna_context"] = ""
            if not vars_map.get("brand_context"):
                vars_map["brand_context"] = ""

        channel_memory_svc = get_channel_memory_service()
        ti = getattr(self, "_last_task_input", None)
        if ti and isinstance(getattr(ti, "payload", None), dict):
            payload = ti.payload
            channel_id_raw = payload.get("channel_id")
            if channel_memory_svc and channel_id_raw:
                try:
                    channel_vars = channel_memory_svc.prompt_variables(UUID(str(channel_id_raw)))
                    for key in ("channel_context", "channel_top_hooks", "channel_top_hashtags"):
                        if not vars_map.get(key) and channel_vars.get(key):
                            vars_map[key] = channel_vars[key]
                except (ValueError, TypeError):
                    pass
            for key in ("specialist_context", "specialist_id", "niche", "specialist_prompt_pack"):
                if payload.get(key) and not vars_map.get(key):
                    vars_map[key] = str(payload[key])
            if payload.get("specialist_context"):
                base_memory = vars_map.get("memory_context", "")
                specialist_block = str(payload["specialist_context"])
                if specialist_block not in base_memory:
                    vars_map["memory_context"] = f"{base_memory}\n\n{specialist_block}".strip()
            creative_block = str(payload.get("creative_memory_context") or "").strip()
            if creative_block:
                base_memory = vars_map.get("memory_context", "")
                if creative_block not in base_memory:
                    vars_map["memory_context"] = f"{base_memory}\n\n[Creative Memory]\n{creative_block}".strip()
        elif not vars_map.get("channel_context"):
            vars_map["channel_context"] = ""

        return service.render(prompt_id, vars_map)

    async def chat_json_with_cache(
        self,
        prompt: RenderedPrompt,
        *,
        topic: str,
        project_id: UUID | None = None,
        pipeline_id: UUID | None = None,
        job_id: UUID | None = None,
    ) -> tuple[dict, bool, str | None]:
        """Call text LLM with optional Redis cache. Returns (data, from_cache, cache_key)."""
        import time

        memory_context = ""
        memory_svc = get_memory_service()
        if memory_svc and project_id:
            memory_context = memory_svc.format_context(project_id)

        provider = "ollama"
        model = ""
        model_mgr = get_model_manager()
        if model_mgr:
            provider, model = model_mgr.provider_and_model(self.step)

        cache_svc = get_cache_service()
        cache_key: str | None = None
        if cache_svc:
            cache_key = cache_svc.make_key(
                agent=self.step,
                topic=topic,
                prompt_version=prompt.version,
                model=model,
                memory_context=memory_context,
            )
            cached = await cache_svc.get(cache_key)
            if cached is not None:
                self._record_cost(
                    project_id=project_id,
                    pipeline_id=pipeline_id,
                    job_id=job_id,
                    provider=provider,
                    model=model,
                    prompt=prompt,
                    data=cached,
                    duration_ms=0,
                    from_cache=True,
                )
                return cached, True, cache_key

        start = time.perf_counter()
        ai = self.get_text_provider()
        data = await ai.chat_json(prompt.system, prompt.user)
        duration_ms = int((time.perf_counter() - start) * 1000)

        if cache_svc and cache_key:
            await cache_svc.set(cache_key, data, agent=self.step)

        self._record_cost(
            project_id=project_id,
            pipeline_id=pipeline_id,
            job_id=job_id,
            provider=provider,
            model=model,
            prompt=prompt,
            data=data,
            duration_ms=duration_ms,
            from_cache=False,
        )

        return data, False, cache_key

    def _record_cost(
        self,
        *,
        project_id: UUID | None,
        pipeline_id: UUID | None,
        job_id: UUID | None,
        provider: str,
        model: str,
        prompt: RenderedPrompt,
        data: dict,
        duration_ms: int,
        from_cache: bool,
    ) -> None:
        tracker = get_cost_tracker()
        if not tracker or not project_id:
            return
        try:
            tracker.record_text_chat(
                project_id=project_id,
                pipeline_id=pipeline_id,
                job_id=job_id,
                agent=self.step,
                provider=provider,
                model=model,
                system=prompt.system,
                user=prompt.user,
                response_data=data,
                duration_ms=duration_ms,
                from_cache=from_cache,
            )
        except Exception:
            pass

    def _provider_model(self, provider_type: str) -> tuple[str, str]:
        manager = get_model_manager()
        if manager:
            cfg = manager.get_config(self.step)
            if cfg.provider_type == provider_type:
                return cfg.provider, cfg.model
        defaults = {
            "speech": ("piper", ""),
            "subtitle": ("local", ""),
            "image": ("local", "pillow-thumbnail"),
            "text": ("ollama", ""),
        }
        return defaults.get(provider_type, ("unknown", ""))

    def _record_speech_cost(
        self,
        task_input: AgentTaskInput,
        *,
        text: str,
        audio_bytes: int,
        duration_ms: int,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        tracker = get_cost_tracker()
        if not tracker:
            return
        prov, mod = self._provider_model("speech")
        try:
            tracker.record_speech(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                job_id=task_input.job_id,
                agent=self.step,
                provider=provider or prov,
                model=model or mod or "default",
                text=text,
                audio_bytes=audio_bytes,
                duration_ms=duration_ms,
            )
        except Exception:
            pass

    def _record_subtitle_cost(
        self,
        task_input: AgentTaskInput,
        *,
        audio_bytes: int,
        segment_count: int,
        duration_ms: int,
        duration_seconds: float | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        tracker = get_cost_tracker()
        if not tracker:
            return
        prov, mod = self._provider_model("subtitle")
        try:
            tracker.record_subtitle(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                job_id=task_input.job_id,
                agent=self.step,
                provider=provider or prov,
                model=model or mod or "default",
                audio_bytes=audio_bytes,
                segment_count=segment_count,
                duration_ms=duration_ms,
                duration_seconds=duration_seconds,
            )
        except Exception:
            pass

    def _record_image_cost(
        self,
        task_input: AgentTaskInput,
        *,
        image_bytes: int,
        duration_ms: int,
        provider: str | None = None,
        model: str | None = None,
        image_count: int = 1,
    ) -> None:
        tracker = get_cost_tracker()
        if not tracker:
            return
        prov, mod = self._provider_model("image")
        try:
            tracker.record_image(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                job_id=task_input.job_id,
                agent=self.step,
                provider=provider or prov,
                model=model or mod or "default",
                image_bytes=image_bytes,
                duration_ms=duration_ms,
                image_count=image_count,
            )
        except Exception:
            pass


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
