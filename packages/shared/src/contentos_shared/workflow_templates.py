"""Built-in workflow templates — seeded into WorkflowDefinition on startup."""

from __future__ import annotations

import os

from contentos_shared.enums import PipelineStep

V1_STEPS: list[str] = [step.value for step in PipelineStep.ordered()]
V2_DYNAMIC_STEPS: list[str] = [step.value for step in PipelineStep.v2_ordered()]
V3_QUALITY_STEPS: list[str] = [step.value for step in PipelineStep.v3_quality_ordered()]
V4_INTELLIGENCE_STEPS: list[str] = [step.value for step in PipelineStep.v4_intelligence_ordered()]
V4_MULTI_TEXT_STEPS: list[str] = [step.value for step in PipelineStep.v4_multi_text_ordered()]
V4_MULTI_FULL_STEPS: list[str] = [step.value for step in PipelineStep.v4_multi_full_ordered()]
FACTORY_FULL_STEPS: list[str] = [step.value for step in PipelineStep.factory_full_ordered()]
V5_MEDIA_AUTOPILOT_STEPS: list[str] = [step.value for step in PipelineStep.v5_media_autopilot_ordered()]

BUILTIN_TEMPLATES: dict[str, dict] = {
    "v1-default": {
        "name": "v1-default",
        "description": "Original 9-step V1 pipeline (research → publisher).",
        "steps": V1_STEPS,
        "config": {},
        "is_default": True,
    },
    "v2-full": {
        "name": "v2-full",
        "description": "V1 pipeline plus V2 async agents (clip research, thumbnail, analytics).",
        "steps": V1_STEPS,
        "config": {
            "enable_clip_pipeline": True,
            "enable_thumbnail": True,
            "enable_analytics_ai": True,
        },
        "is_default": False,
    },
    "v2-dynamic": {
        "name": "v2-dynamic",
        "description": "Full 16-step V2 pipeline with clip research, media analyze, asset search, thumbnail and analytics.",
        "steps": V2_DYNAMIC_STEPS,
        "config": {
            "enable_clip_pipeline": True,
            "enable_media_analyze": True,
        },
        "is_default": False,
    },
    "v3-quality": {
        "name": "v3-quality",
        "description": "V3 quality — Hook, reviews, emotion, storyboard, video review.",
        "steps": V3_QUALITY_STEPS,
        "config": {
            "enable_trend_intelligence": True,
            "enable_hook_generator": True,
            "enable_script_reviewer": True,
            "enable_emotion_analyzer": True,
            "enable_storyboard": True,
            "enable_scene_director": True,
            "enable_video_reviewer": True,
            "enable_creative_retry": True,
        },
        "is_default": False,
    },
    "v4-intelligence": {
        "name": "v4-intelligence",
        "description": "V4 — v3-quality plus content intelligence (viral score + reuse) before scenes.",
        "steps": V4_INTELLIGENCE_STEPS,
        "config": {
            "enable_trend_intelligence": True,
            "enable_hook_generator": True,
            "enable_script_reviewer": True,
            "enable_emotion_analyzer": True,
            "enable_content_intelligence": True,
            "enable_storyboard": True,
            "enable_scene_director": True,
            "enable_video_reviewer": True,
            "enable_creative_retry": True,
            "enable_learning": True,
        },
        "is_default": False,
    },
    "v4-multi-text": {
        "name": "v4-multi-text",
        "description": "V4.2 — v4-intelligence plus multi-content text (thread, LinkedIn, newsletter, SEO, email).",
        "steps": V4_MULTI_TEXT_STEPS,
        "config": {
            "enable_trend_intelligence": True,
            "enable_hook_generator": True,
            "enable_script_reviewer": True,
            "enable_emotion_analyzer": True,
            "enable_content_intelligence": True,
            "enable_multi_content": True,
            "enable_storyboard": True,
            "enable_scene_director": True,
            "enable_video_reviewer": True,
            "enable_creative_retry": True,
            "enable_learning": True,
        },
        "is_default": False,
    },
    "v4-multi-full": {
        "name": "v4-multi-full",
        "description": "V4.2 — text + video platform variants (TikTok, Shorts, Reels) from same render.",
        "steps": V4_MULTI_FULL_STEPS,
        "config": {
            "enable_trend_intelligence": True,
            "enable_hook_generator": True,
            "enable_script_reviewer": True,
            "enable_emotion_analyzer": True,
            "enable_content_intelligence": True,
            "enable_multi_content": True,
            "enable_multi_content_video": True,
            "enable_storyboard": True,
            "enable_scene_director": True,
            "enable_video_reviewer": True,
            "enable_creative_retry": True,
            "enable_learning": True,
        },
        "is_default": False,
    },
    "factory-full": {
        "name": "factory-full",
        "description": "Complete executable factory line from idea to publisher, using current production handlers.",
        "steps": FACTORY_FULL_STEPS,
        "config": {
            "enable_trend_intelligence": True,
            "enable_hook_generator": True,
            "enable_script_reviewer": True,
            "enable_storyboard": True,
            "enable_scene_director": True,
            "enable_clip_pipeline": True,
            "enable_thumbnail": True,
            "enable_video_reviewer": True,
            "enable_auto_retry": True,
            "enable_creative_retry": True,
            "enable_content_score": True,
            "enable_content_intelligence": True,
            "enable_learning": True,
            "enable_knowledge_base": True,
            "enable_analytics_ai": True,
            "enable_media_analyze": True,
            "enable_take_recommendation": True,
            "enable_retention": True,
            "enable_seo": True,
            "enable_ai_director": True,
            "enable_creative_memory": True,
        },
        "is_default": False,
    },
    "v5-media-autopilot": {
        "name": "v5-media-autopilot",
        "description": "V5 media autopilot — licensed B-roll, media analyze, take recommendation, auto edit to MP4.",
        "steps": V5_MEDIA_AUTOPILOT_STEPS,
        "config": {
            "enable_clip_pipeline": True,
            "enable_media_analyze": True,
            "enable_take_recommendation": True,
            "enable_v5_media_autopilot": True,
            "enable_retention": True,
            "enable_seo": True,
            "enable_ai_director": True,
            "enable_creative_memory": True,
            "default_topic_hint": "GTA 6",
            "content_sources": ["pexels", "pixabay", "own_library", "local_library"],
        },
        "is_default": False,
    },
}


def get_builtin(name: str) -> dict | None:
    return BUILTIN_TEMPLATES.get(name)


def get_default_workflow_name() -> str:
    return os.getenv("DEFAULT_WORKFLOW", "v1-default")


def list_builtin_names() -> list[str]:
    return list(BUILTIN_TEMPLATES.keys())

