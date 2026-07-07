"""Publisher Agent — metadata + platform plugins (TikTok, YouTube, Instagram)."""

import json
import os
from urllib.parse import urlparse, urlunparse
from uuid import UUID, uuid4

from contentos_database.platform_publications import persist_platform_publications
from contentos_database.publish_credentials import load_merged_project_credentials
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.audiovisual_qa import normalize_publish_mode, should_block_live_publish
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.plugins.context import PublishContext
from contentos_shared.plugins.loader import ensure_plugins_loaded, run_post_publish
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta, AssetRef


class PublisherAgentHandler(BaseAgentHandler):
    step = "publisher"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        ensure_plugins_loaded()
        script = task_input.payload.get("script", {})
        topic = task_input.payload.get("topic") or script.get("title", "")
        logs = [f"Preparing publication for: {topic}"]

        if task_input.payload.get("factory_publish_hold") and not task_input.payload.get(
            "factory_publish_approved"
        ):
            batch_id = task_input.payload.get("factory_batch_id", "")
            logs.append(f"Batch publish hold active (batch={batch_id}) — awaiting human approval")
            publication = {
                "title": script.get("title", topic),
                "description": "",
                "hashtags": [],
                "status": "pending_batch_approval",
                "mode": os.getenv("PUBLISH_MODE", "dry_run"),
                "platforms": {},
                "factory_batch_id": batch_id,
            }
            ref = await self.get_asset_manager().store(
                AssetCategory.ASSETS,
                json.dumps(publication, ensure_ascii=False).encode(),
                AssetMeta(
                    project_id=task_input.project_id,
                    pipeline_id=task_input.pipeline_id,
                    filename="publication.json",
                    content_type="application/json",
                ),
            )
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.COMPLETED.value,
                artifacts=[ref],
                data={"publication": publication, "factory_publish_held": True},
                logs=logs,
            )

        seo_pkg = task_input.payload.get("seo_package") or {}
        if isinstance(seo_pkg, dict) and seo_pkg.get("title"):
            base_metadata = {
                "title": seo_pkg.get("title", topic),
                "description": seo_pkg.get("description", ""),
                "hashtags": seo_pkg.get("hashtags", []),
            }
            logs.append(f"Using SEO package (score={seo_pkg.get('seo_score', 'n/a')})")
        else:
            prompt = self.render_prompt(
                "publisher",
                {"topic": topic, "script_json": json.dumps(script, ensure_ascii=False)},
                project_id=task_input.project_id,
            )
            logs.append(f"Prompt v{prompt.version}")
            base_metadata, from_cache, cache_key = await self.chat_json_with_cache(
                prompt,
                topic=topic,
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                job_id=task_input.job_id,
            )
            if from_cache:
                logs.append(f"Cache hit ({cache_key})")

        credentials = self._load_credentials_from_env()
        credentials = await load_merged_project_credentials(task_input.project_id, credentials)
        render_ref = task_input.payload.get("render_ref")
        render_bytes = await self._load_render_bytes(render_ref, logs)
        render_public_url = await self._resolve_render_public_url(render_ref, logs)

        mode = normalize_publish_mode()
        factory_approved = bool(task_input.payload.get("factory_publish_approved"))
        blocked, qa_gate = should_block_live_publish(
            task_input.payload,
            mode=mode,
            factory_publish_approved=factory_approved,
        )
        logs.append(
            f"QA gate publishable={qa_gate['publishable']} enforced={qa_gate.get('qa_enforced', True)}"
        )
        if blocked:
            logs.append("Live publish blocked — QA gate failed: " + ", ".join(qa_gate["block_reasons"]))
            publication = {
                "title": base_metadata.get("title", topic),
                "description": base_metadata.get("description", ""),
                "hashtags": base_metadata.get("hashtags", []),
                "status": "blocked_qa",
                "mode": mode,
                "platforms": {},
                "audiovisual_qa_gate": qa_gate,
            }
            ref = await self.get_asset_manager().store(
                AssetCategory.ASSETS,
                json.dumps(publication, ensure_ascii=False).encode(),
                AssetMeta(
                    project_id=task_input.project_id,
                    pipeline_id=task_input.pipeline_id,
                    filename="publication.json",
                    content_type="application/json",
                ),
            )
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.COMPLETED.value,
                artifacts=[ref],
                data={
                    "publication": publication,
                    "audiovisual_qa_gate": qa_gate,
                    "publish_blocked": True,
                },
                logs=logs,
            )

        context = PublishContext(
            pipeline_id=task_input.pipeline_id,
            project_id=task_input.project_id,
            topic=topic,
            script=script,
            base_metadata=base_metadata,
            render_ref=render_ref,
            render_bytes=render_bytes,
            render_public_url=render_public_url,
            credentials=credentials,
        )

        platform_publications = await run_post_publish(context)
        await self._persist_publication_audit(
            task_input.project_id,
            task_input.pipeline_id,
            mode,
            platform_publications,
            logs,
        )
        logs.append(f"Publish mode: {mode}")
        for platform, pub in platform_publications.items():
            logs.append(
                f"  {platform}: {pub.get('status')} "
                f"id={pub.get('external_id') or '—'} "
                f"url={pub.get('publish_url') or '—'}"
            )

        publication = {
            "title": base_metadata.get("title", topic),
            "description": base_metadata.get("description", ""),
            "hashtags": base_metadata.get("hashtags", []),
            "status": "ready",
            "mode": mode,
            "platforms": platform_publications,
            "audiovisual_qa_gate": qa_gate,
        }

        ref = await self.get_asset_manager().store(
            AssetCategory.ASSETS,
            json.dumps(publication, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="publication.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={"publication": publication, "platform_publications": platform_publications, "audiovisual_qa_gate": qa_gate},
            logs=logs,
        )

    def _load_credentials_from_env(self) -> dict[str, dict]:
        """Load channel credentials from env JSON (optional)."""
        raw = os.getenv("PLATFORM_CREDENTIALS_JSON", "{}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    async def _load_render_bytes(self, render_ref: dict | None, logs: list[str]) -> bytes | None:
        if not render_ref or not render_ref.get("key"):
            logs.append("No render_ref available for platform upload")
            return None
        ref = AssetRef(
            id=uuid4(),
            category=AssetCategory.RENDERS,
            key=render_ref["key"],
            bucket=render_ref.get("bucket", "contentos"),
            content_type="video/mp4",
        )
        try:
            data = await self.get_asset_manager().get(ref)
            logs.append(f"Render loaded for publishing ({len(data)} bytes)")
            return data
        except Exception as exc:
            logs.append(f"Could not load render for publishing: {exc}")
            return None

    async def _resolve_render_public_url(self, render_ref: dict | None, logs: list[str]) -> str | None:
        if not render_ref or not render_ref.get("key"):
            return None
        ref = AssetRef(
            id=uuid4(),
            category=AssetCategory.RENDERS,
            key=render_ref["key"],
            bucket=render_ref.get("bucket", "contentos"),
            content_type="video/mp4",
        )
        try:
            url = await self.get_asset_manager().get_presigned_url(ref, expires=7200)
            public_host = os.getenv("MINIO_PUBLIC_ENDPOINT", "").strip()
            if public_host:
                parsed = urlparse(url)
                host = public_host if "://" in public_host else f"http://{public_host}"
                public = urlparse(host)
                url = urlunparse(parsed._replace(netloc=public.netloc or public.path, scheme=public.scheme or "http"))
            logs.append("Render presigned URL ready for Instagram/live plugins")
            return url
        except Exception as exc:
            logs.append(f"Could not presign render URL: {exc}")
            return None

    @staticmethod
    async def _persist_publication_audit(
        project_id: UUID,
        pipeline_id: UUID,
        mode: str,
        platforms: dict,
        logs: list[str],
    ) -> None:
        try:
            count = await persist_platform_publications(project_id, pipeline_id, mode, platforms)
            if count:
                logs.append(f"Publication audit persisted ({count} platforms)")
        except Exception as exc:
            logs.append(f"Publication audit persist skipped: {exc}")
