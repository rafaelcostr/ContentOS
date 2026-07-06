"""Cost tracking application service."""

from __future__ import annotations

import json
import time
from functools import lru_cache
from uuid import UUID

from contentos_cost.domain.cost_entry import CostRecord
from contentos_cost.infrastructure.db_repository import CostRepository, record_sync
from contentos_cost.infrastructure.pricing_table import (
    estimate_audio_minutes,
    estimate_cost_usd,
    estimate_image_cost_usd,
    estimate_speech_cost_usd,
    estimate_subtitle_cost_usd,
    estimate_tokens,
)
from sqlalchemy.ext.asyncio import AsyncSession


class CostTracker:
    def __init__(self) -> None:
        self._repo = CostRepository()

    def record_text_chat(
        self,
        *,
        project_id: UUID,
        pipeline_id: UUID | None,
        job_id: UUID | None,
        agent: str,
        provider: str,
        model: str,
        system: str,
        user: str,
        response_data: dict,
        duration_ms: int,
        from_cache: bool = False,
    ) -> CostRecord:
        tokens_in = 0 if from_cache else estimate_tokens(system + user)
        tokens_out = 0 if from_cache else estimate_tokens(json.dumps(response_data, ensure_ascii=False))
        cost = estimate_cost_usd(provider, model, tokens_in, tokens_out, from_cache=from_cache)
        entry = CostRecord(
            project_id=project_id,
            pipeline_id=pipeline_id,
            job_id=job_id,
            agent=agent,
            provider=provider,
            model=model,
            operation="text_chat",
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            duration_ms=duration_ms,
            estimated_cost_usd=cost,
            from_cache=from_cache,
        )
        record_sync(entry)
        return entry

    def record_speech(
        self,
        *,
        project_id: UUID,
        pipeline_id: UUID | None,
        job_id: UUID | None,
        agent: str,
        provider: str,
        model: str,
        text: str,
        audio_bytes: int,
        duration_ms: int,
    ) -> CostRecord:
        chars = len(text or "")
        cost = estimate_speech_cost_usd(provider, chars)
        entry = CostRecord(
            project_id=project_id,
            pipeline_id=pipeline_id,
            job_id=job_id,
            agent=agent,
            provider=provider,
            model=model,
            operation="speech_tts",
            tokens_input=chars,
            tokens_output=max(audio_bytes // 100, 0),
            duration_ms=duration_ms,
            estimated_cost_usd=cost,
            from_cache=False,
        )
        record_sync(entry)
        return entry

    def record_subtitle(
        self,
        *,
        project_id: UUID,
        pipeline_id: UUID | None,
        job_id: UUID | None,
        agent: str,
        provider: str,
        model: str,
        audio_bytes: int,
        segment_count: int,
        duration_ms: int,
        duration_seconds: float | None = None,
    ) -> CostRecord:
        minutes = estimate_audio_minutes(audio_bytes, duration_seconds)
        # Store centi-minutes in tokens_input for overview aggregation without schema change
        tokens_in = int(minutes * 100)
        cost = estimate_subtitle_cost_usd(
            provider,
            audio_bytes=audio_bytes,
            duration_seconds=duration_seconds,
        )
        entry = CostRecord(
            project_id=project_id,
            pipeline_id=pipeline_id,
            job_id=job_id,
            agent=agent,
            provider=provider,
            model=model,
            operation="subtitle_stt",
            tokens_input=tokens_in,
            tokens_output=max(segment_count, 0),
            duration_ms=duration_ms,
            estimated_cost_usd=cost,
            from_cache=False,
        )
        record_sync(entry)
        return entry

    def record_image(
        self,
        *,
        project_id: UUID,
        pipeline_id: UUID | None,
        job_id: UUID | None,
        agent: str,
        provider: str,
        model: str,
        image_bytes: int,
        duration_ms: int,
        image_count: int = 1,
    ) -> CostRecord:
        cost = estimate_image_cost_usd(provider, image_count)
        entry = CostRecord(
            project_id=project_id,
            pipeline_id=pipeline_id,
            job_id=job_id,
            agent=agent,
            provider=provider,
            model=model,
            operation="image_generate",
            tokens_input=0,
            tokens_output=max(image_count, 0),
            duration_ms=duration_ms,
            estimated_cost_usd=cost,
            from_cache=False,
        )
        record_sync(entry)
        return entry

    async def overview(self, db: AsyncSession, project_ids: list[UUID] | None = None) -> dict:
        return await self._repo.overview(db, project_ids)

    async def by_project(self, db: AsyncSession, project_id: UUID) -> dict:
        return await self._repo.by_project(db, project_id)

    async def by_pipeline(self, db: AsyncSession, pipeline_id: UUID) -> dict:
        return await self._repo.by_pipeline(db, pipeline_id)


@lru_cache(maxsize=1)
def get_cost_tracker() -> CostTracker:
    return CostTracker()


class CostTimer:
    """Context manager for measuring duration_ms."""

    def __enter__(self) -> "CostTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args) -> None:
        pass

    @property
    def duration_ms(self) -> int:
        return int((time.perf_counter() - self._start) * 1000)
