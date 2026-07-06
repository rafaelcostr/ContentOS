"""Analytics AI application service."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any
from uuid import UUID

from contentos_analytics_ai.domain.insight import AnalyticsInsightData
from contentos_analytics_ai.infrastructure.db_repository import InsightRepository, save_sync
from sqlalchemy.ext.asyncio import AsyncSession


class AnalyticsService:
    def __init__(self) -> None:
        self._repo = InsightRepository()

    def collect_metrics(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Build metrics dict from pipeline payload; uses platform data or estimates."""
        publication = payload.get("publication") or {}
        platform_pubs = publication.get("platforms") or payload.get("platform_publications") or {}

        views = 0
        likes = 0
        for pub in platform_pubs.values():
            if isinstance(pub, dict):
                views += int(pub.get("views") or pub.get("view_count") or 0)
                likes += int(pub.get("likes") or pub.get("like_count") or 0)

        source = "platform" if views > 0 else "estimated"
        return {
            "views": views,
            "likes": likes,
            "retention_pct": payload.get("retention_pct", 0),
            "ctr_pct": payload.get("ctr_pct", 0),
            "duration_seconds": payload.get("duration_seconds"),
            "title": publication.get("title") or payload.get("topic", ""),
            "hashtags": publication.get("hashtags", []),
            "source": source,
        }

    def collect_models_used(self) -> dict[str, dict[str, str]]:
        try:
            from contentos_models import get_model_manager

            mgr = get_model_manager()
            agents = ["research", "script", "scene", "publisher", "analytics"]
            out: dict[str, dict[str, str]] = {}
            for agent in agents:
                provider, model = mgr.provider_and_model(agent)
                out[agent] = {"provider": provider, "model": model}
            return out
        except Exception:
            return {}

    def collect_prompts_used(self) -> dict[str, str]:
        try:
            from contentos_prompts import get_prompt_service

            svc = get_prompt_service()
            svc.reload()
            ids = ["research", "script", "scene", "publisher", "analytics"]
            out: dict[str, str] = {}
            for pid in ids:
                try:
                    out[pid] = svc.get_prompt(pid).version
                except Exception:
                    pass
            return out
        except Exception:
            return {}

    def save_insight(self, data: AnalyticsInsightData) -> bool:
        return save_sync(data)

    async def get_insight(self, db: AsyncSession, pipeline_id: UUID) -> dict | None:
        return await self._repo.get_by_pipeline(db, pipeline_id)

    async def list_insights(self, db: AsyncSession, limit: int = 50) -> list[dict]:
        return await self._repo.list_recent(db, limit)

    def apply_to_memory(self, project_id: UUID, analysis: dict[str, Any], pipeline_id: UUID) -> bool:
        """Append analysis to project memory history and optional style tweaks."""
        try:
            from contentos_memory.infrastructure.db_repository import load_sync, upsert_sync

            memory = load_sync(project_id)
            entry = {
                "pipeline_id": str(pipeline_id),
                "summary": analysis.get("summary", ""),
                "score": analysis.get("score"),
                "suggestions": (analysis.get("suggestions") or [])[:5],
            }
            memory.history = [entry] + (memory.history or [])[:9]

            for tweak in (analysis.get("recommended_prompt_tweaks") or [])[:3]:
                if isinstance(tweak, dict):
                    for key, value in tweak.items():
                        if key in ("tone", "hook_style", "cta", "niche", "goal"):
                            setattr(memory, key, str(value))
                        else:
                            memory.style[key] = value

            return upsert_sync(memory)
        except Exception:
            return False

    def auto_apply_enabled(self) -> bool:
        return os.getenv("ANALYTICS_AUTO_APPLY_MEMORY", "false").lower() in ("true", "1", "yes")


@lru_cache(maxsize=1)
def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()
