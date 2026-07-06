"""Asset Collector Agent — fetch and register clips from content sources (V2 async)."""

import json

from contentos_agents.handlers._pipeline_base import PipelineAwareHandler
from contentos_agents.handlers._storage import agent_storage_settings
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta
from contentos_storage.application.asset_pipeline_service import AssetPipelineService
from contentos_storage.domain.asset_metadata import normalize_asset_metadata
from contentos_storage.factory import get_asset_manager

try:
    from contentos_sources import get_collection_store, get_source_manager
except ImportError:

    def get_source_manager():  # type: ignore[misc]
        return None

    def get_collection_store():  # type: ignore[misc]
        return None


class AssetCollectorAgentHandler(PipelineAwareHandler):
    step = "asset_collector"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        scene_candidates = task_input.payload.get("scene_candidates", [])
        logs = [f"[asset_collector] collecting for {len(scene_candidates)} scenes"]
        mgr = get_source_manager()
        if not mgr:
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.FAILED.value,
                error="content-sources not available",
                logs=logs,
            )

        pipeline = AssetPipelineService(get_asset_manager(agent_storage_settings()))
        collected: list[dict] = []
        topic = task_input.payload.get("topic") or task_input.payload.get("script", {}).get("title", "")
        scenes = task_input.payload.get("scenes") or []

        for scene in scene_candidates:
            label = scene.get("scene_label", "scene")
            candidates = scene.get("candidates") or []
            if not candidates:
                continue
            top = candidates[0]
            source_id = top.get("source_id")
            candidate_id = top.get("candidate_id")
            if not source_id or not candidate_id:
                continue
            try:
                asset = await mgr.fetch(source_id, candidate_id)
                if asset.content_type.startswith("application/json"):
                    logs.append(f"Skip non-media RSS ref for {label}")
                    continue

                scene_plan = next((s for s in scenes if s.get("label") == label), {}) or {}
                search_meta = normalize_asset_metadata(
                    topic=topic,
                    scene={**scene_plan, "scene_label": label, "label": label},
                    candidate=top,
                    extra={
                        "source_id": source_id,
                        "candidate_id": candidate_id,
                        **(getattr(asset, "metadata", None) or {}),
                    },
                )

                meta = AssetMeta(
                    project_id=task_input.project_id,
                    pipeline_id=task_input.pipeline_id,
                    filename=asset.filename,
                    content_type=asset.content_type,
                    tags={"source": source_id, "scene": label},
                )
                persisted = await pipeline.store_and_persist(
                    AssetCategory.TAKES,
                    asset.data,
                    meta,
                    extra_tags=[source_id, label],
                    metadata=search_meta,
                )
                if persisted.deduplicated:
                    logs.append(f"Dedup reuse {label} -> {persisted.ref.key}")

                collected.append(
                    {
                        "scene_label": label,
                        "source_id": source_id,
                        "candidate_id": candidate_id,
                        "asset_key": persisted.ref.key,
                        "bucket": persisted.ref.bucket,
                        "asset_id": str(persisted.asset_id),
                        "sha256": asset.sha256,
                        "deduplicated": persisted.deduplicated,
                    }
                )
                logs.append(f"Collected {label} -> {persisted.ref.key}")
            except Exception as exc:
                logs.append(f"Failed {label}: {exc}")

        store = get_collection_store()
        if store:
            store.save_assets(task_input.pipeline_id, task_input.project_id, collected)

        ref = None
        if collected:
            manifest = await pipeline.store_and_persist(
                AssetCategory.ASSETS,
                json.dumps({"assets": collected}, ensure_ascii=False).encode(),
                AssetMeta(
                    project_id=task_input.project_id,
                    pipeline_id=task_input.pipeline_id,
                    filename="collected_assets.json",
                    content_type="application/json",
                    tags={"type": "manifest"},
                ),
                extra_tags=["manifest", "asset_collector"],
            )
            ref = manifest.ref

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref] if ref else [],
            data={"assets": collected, "count": len(collected)},
            logs=logs,
        )
