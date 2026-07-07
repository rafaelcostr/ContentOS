"""Asset Collector Agent — fetch and register clips from content sources (V2 async)."""

import json
import os

from contentos_agents.handlers._pipeline_base import PipelineAwareHandler
from contentos_agents.handlers._storage import agent_storage_settings
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.media_production import require_media_assets
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
        collected_by_scene: dict[str, int] = {}
        topic = task_input.payload.get("topic") or task_input.payload.get("script", {}).get("title", "")
        scenes = task_input.payload.get("scenes") or []
        expected_labels = _expected_scene_labels(scenes, scene_candidates)
        min_per_scene = _media_min_assets_per_scene()

        for scene in scene_candidates:
            label = scene.get("scene_label", "scene")
            candidates = scene.get("candidates") or []
            if not candidates:
                continue
            top_n = max(1, int(os.getenv("MEDIA_COLLECT_TOP_N", "1")))
            for top in candidates[:top_n]:
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
                            "license_type": search_meta.get("license_type"),
                            "license": search_meta.get("license") or search_meta.get("license_type"),
                            "source_url": search_meta.get("source_url"),
                            "author": search_meta.get("author"),
                            "duration_seconds": search_meta.get("duration_seconds") or top.get("duration_seconds"),
                        }
                    )
                    collected_by_scene[label] = collected_by_scene.get(label, 0) + 1
                    logs.append(f"Collected {label} ({source_id}) -> {persisted.ref.key}")
                except Exception as exc:
                    logs.append(f"Failed {label} ({source_id}/{candidate_id}): {exc}")

        store = get_collection_store()
        if store:
            store.save_assets(task_input.pipeline_id, task_input.project_id, collected)

        coverage = _coverage_report(expected_labels, collected_by_scene, min_per_scene)
        if coverage["missing_scene_labels"]:
            logs.append(
                "Missing media for scenes: "
                + ", ".join(str(label) for label in coverage["missing_scene_labels"])
            )

        ref = None
        if collected:
            manifest = await pipeline.store_and_persist(
                AssetCategory.ASSETS,
                json.dumps(
                    {
                        "assets": collected,
                        "coverage": coverage,
                    },
                    ensure_ascii=False,
                ).encode(),
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

        if require_media_assets() and not coverage["passed"]:
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.FAILED.value,
                error=(
                    "insufficient media assets: "
                    + ", ".join(str(label) for label in coverage["missing_scene_labels"])
                ),
                data={"assets": collected, "count": len(collected), "media_coverage": coverage},
                logs=logs,
            )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref] if ref else [],
            data={"assets": collected, "count": len(collected), "media_coverage": coverage},
            logs=logs,
        )


def _media_min_assets_per_scene() -> int:
    try:
        return max(1, int(os.getenv("MEDIA_MIN_ASSETS_PER_SCENE", "1")))
    except ValueError:
        return 1


def _expected_scene_labels(scenes: list[dict], scene_candidates: list[dict]) -> list[str]:
    labels: list[str] = []
    for index, scene in enumerate(scenes):
        label = str(scene.get("label") or scene.get("scene_label") or f"scene_{index}")
        if label not in labels:
            labels.append(label)
    for index, scene in enumerate(scene_candidates):
        label = str(scene.get("scene_label") or scene.get("label") or f"scene_{index}")
        if label not in labels:
            labels.append(label)
    return labels


def _coverage_report(labels: list[str], collected_by_scene: dict[str, int], min_per_scene: int) -> dict:
    missing = [label for label in labels if collected_by_scene.get(label, 0) < min_per_scene]
    return {
        "expected_scene_count": len(labels),
        "covered_scene_count": len(labels) - len(missing),
        "min_assets_per_scene": min_per_scene,
        "missing_scene_labels": missing,
        "assets_per_scene": {label: collected_by_scene.get(label, 0) for label in labels},
        "passed": not missing,
    }
