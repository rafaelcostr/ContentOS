"""Asset Search Agent — match indexed video assets to planned scenes (V5.0.4 take recommendation)."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from contentos_database.models import Asset
from contentos_intelligence.application.take_recommendation.service import TakeRecommendationService
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from sqlalchemy import or_, select
from sqlalchemy.orm import Session


def _sync_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "")
    return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )


class AssetSearchAgentHandler(BaseAgentHandler):
    step = "asset_search"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        scenes = task_input.payload.get("scenes", [])
        collected = task_input.payload.get("assets", [])
        topic = task_input.payload.get("topic") or task_input.payload.get("script", {}).get("title", "")
        logs = [f"[asset_search] matching assets for {len(scenes)} scenes"]

        assets = self._load_assets(task_input)
        if assets:
            logs.append(f"Loaded {len(assets)} indexed video assets")
        else:
            logs.append("No indexed assets found; falling back to collected manifest")

        recommender = TakeRecommendationService(database_url=os.getenv("DATABASE_URL"))
        if recommender.enabled:
            logs.append("TakeRecommendationService enabled")
        else:
            logs.append("TakeRecommendationService disabled — token/media scoring only")

        matches = await recommender.recommend_scenes(
            topic=str(topic),
            scenes=scenes,
            assets=assets,
            collected=collected,
        )

        selected = [m["selected"] for m in matches if m.get("selected")]
        missing = [m.get("scene_label") for m in matches if not m.get("selected")]
        coverage = {
            "expected_scene_count": len(scenes),
            "matched_scene_count": len(selected),
            "missing_scene_labels": missing,
            "passed": not missing,
        }
        for match in matches:
            selected_item = match.get("selected") or {}
            if selected_item.get("score") is not None:
                logs.append(
                    f"  {match.get('scene_label')}: score={selected_item['score']} "
                    f"reasons={selected_item.get('reasons', [])}"
                )
        logs.append(f"Matched {len(selected)}/{max(len(scenes), 1)} scenes")
        if missing:
            logs.append("Missing asset matches for scenes: " + ", ".join(str(label) for label in missing))

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            data={
                "asset_matches": matches,
                "assets_selected": selected,
                "asset_search_count": len(selected),
                "asset_match_coverage": coverage,
                "take_recommendation": recommender.enabled,
            },
            logs=logs,
        )

    def _match_scenes(
        self,
        scenes: list[dict],
        assets: list[Asset],
        collected: list[dict],
        topic: str,
    ) -> list[dict[str, Any]]:
        """Sync helper for tests and legacy callers."""
        recommender = TakeRecommendationService()
        return asyncio.run(
            recommender.recommend_scenes(
                topic=topic,
                scenes=scenes,
                assets=assets,
                collected=collected,
            )
        )

    def _load_assets(self, task_input: AgentTaskInput) -> list[Asset]:
        database_url = _sync_database_url()
        if not database_url:
            return []
        try:
            from sqlalchemy import create_engine

            engine = create_engine(database_url, pool_pre_ping=True)
            with Session(engine) as session:
                result = session.execute(
                    select(Asset)
                    .where(
                        Asset.category == AssetCategory.TAKES.value,
                        or_(
                            Asset.pipeline_id == task_input.pipeline_id,
                            Asset.project_id == task_input.project_id,
                            Asset.project_id.is_(None),
                        ),
                    )
                    .order_by(Asset.created_at.desc())
                    .limit(500)
                )
                return list(result.scalars().all())
        except Exception:
            return []
