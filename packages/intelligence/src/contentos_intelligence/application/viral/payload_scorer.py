"""PayloadViralityScorer — IViralityScorer from pipeline payload (Epic 1)."""

from __future__ import annotations

from contentos_intelligence.application.viral import analyzers
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.viral_report import ViralReport


class PayloadViralityScorer:
    """Aggregates V3 agent outputs into a single ViralReport — no extra LLM calls."""

    async def analyze(self, context: IntelligenceContext) -> ViralReport:
        payload = context.payload or {}
        hook_score = analyzers.analyze_hook(payload)
        emotion_score, emotion_details = analyzers.analyze_emotion(payload)
        rhythm_score = analyzers.analyze_rhythm(payload)
        scene_score = analyzers.analyze_scenes(payload)
        trend_score = analyzers.analyze_trend(payload)
        cta_score = analyzers.analyze_cta(payload)
        retention = analyzers.predict_retention(hook_score, emotion_details, rhythm_score)
        viral_score = analyzers.compute_viral_score(
            hook_score=hook_score,
            emotion_score=emotion_score,
            rhythm_score=rhythm_score,
            scene_score=scene_score,
            trend_score=trend_score,
            cta_score=cta_score,
            retention_prediction=retention,
        )
        recommendations = analyzers.build_recommendations(
            hook_score=hook_score,
            emotion_score=emotion_score,
            rhythm_score=rhythm_score,
            scene_score=scene_score,
            trend_score=trend_score,
            cta_score=cta_score,
            retention_prediction=retention,
            emotion_details=emotion_details,
        )
        return ViralReport(
            viral_score=viral_score,
            retention_prediction=retention,
            recommendations=recommendations,
            hook_score=hook_score,
            rhythm_score=rhythm_score,
            emotion_score=emotion_score,
            scene_score=scene_score,
            cta_score=cta_score,
            details={
                "trend_score": trend_score,
                "emotion": emotion_details,
                "topic": context.topic,
                "pipeline_id": str(context.pipeline_id) if context.pipeline_id else None,
            },
        )
