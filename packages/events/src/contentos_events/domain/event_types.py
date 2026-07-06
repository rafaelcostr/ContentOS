"""Domain event type constants.

Wire format is always `resource.action` (snake.case).
PascalCase names in the V3 mission are documented aliases only (ADR-003).
"""

# Pipeline lifecycle
PIPELINE_CREATED = "pipeline.created"
PIPELINE_COMPLETED = "pipeline.completed"
PIPELINE_FAILED = "pipeline.failed"

# Step / agent lifecycle (V1 compatible)
STEP_STARTED = "step.started"
STEP_COMPLETED = "step.completed"
STEP_FAILED = "step.failed"
STEP_RETRY = "step.retry"

# Domain events (V1 + V2)
RESEARCH_FINISHED = "research.finished"
SCRIPT_STARTED = "script.started"
SCRIPT_FINISHED = "script.finished"
SCENE_CREATED = "scene.created"
VOICE_GENERATED = "voice.generated"
SUBTITLE_CREATED = "subtitle.created"
EDITOR_FINISHED = "editor.finished"
QUALITY_APPROVED = "quality.approved"
QUALITY_REJECTED = "quality.rejected"
PUBLISHER_FINISHED = "publisher.finished"
THUMBNAIL_CREATED = "thumbnail.created"
ANALYTICS_PROCESSED = "analytics.processed"

# V2 pipeline steps (Tier A1)
CLIP_RESEARCH_FINISHED = "clip_research.finished"
ASSETS_READY = "assets.ready"
ASSET_INDEX_FINISHED = "asset_index.finished"
TAKES_FINISHED = "takes.finished"

# V3 creative agents (Tier B1–B9)
TREND_INTELLIGENCE_FINISHED = "trend_intelligence.finished"
HOOK_FINISHED = "hook.finished"
SCRIPT_REVIEW_FINISHED = "script_review.finished"
EMOTION_FINISHED = "emotion.finished"
VIDEO_REVIEW_FINISHED = "video_review.finished"
STORYBOARD_FINISHED = "storyboard.finished"
SCENE_DIRECTOR_FINISHED = "scene_director.finished"
CREATIVE_RETRY_STARTED = "creative_retry.started"
CREATIVE_RETRY_EXHAUSTED = "creative_retry.exhausted"

CONTENT_INTELLIGENCE_FINISHED = "content_intelligence.finished"
REUSE_SUGGESTED = "reuse.suggested"
AB_VARIANT_SELECTED = "ab.variant.selected"
CONTENT_SCORE_COMPUTED = "content_score.computed"
SPECIALIST_SELECTED = "specialist.selected"
MULTI_CONTENT_GENERATED = "multi_content.generated"
VIDEO_VARIANTS_GENERATED = "video_variants.generated"
LEARNING_RECORDED = "learning.recorded"
TREND_FORECASTED = "trend.forecasted"
GRAPH_UPDATED = "graph.updated"

ALL_TYPES = [
    PIPELINE_CREATED,
    PIPELINE_COMPLETED,
    PIPELINE_FAILED,
    STEP_STARTED,
    STEP_COMPLETED,
    STEP_FAILED,
    STEP_RETRY,
    RESEARCH_FINISHED,
    SCRIPT_STARTED,
    SCRIPT_FINISHED,
    SCENE_CREATED,
    VOICE_GENERATED,
    SUBTITLE_CREATED,
    EDITOR_FINISHED,
    QUALITY_APPROVED,
    QUALITY_REJECTED,
    PUBLISHER_FINISHED,
    THUMBNAIL_CREATED,
    ANALYTICS_PROCESSED,
    CLIP_RESEARCH_FINISHED,
    ASSETS_READY,
    ASSET_INDEX_FINISHED,
    TAKES_FINISHED,
    TREND_INTELLIGENCE_FINISHED,
    HOOK_FINISHED,
    SCRIPT_REVIEW_FINISHED,
    EMOTION_FINISHED,
    VIDEO_REVIEW_FINISHED,
    STORYBOARD_FINISHED,
    SCENE_DIRECTOR_FINISHED,
    CREATIVE_RETRY_STARTED,
    CREATIVE_RETRY_EXHAUSTED,
    CONTENT_INTELLIGENCE_FINISHED,
    REUSE_SUGGESTED,
    AB_VARIANT_SELECTED,
    CONTENT_SCORE_COMPUTED,
    SPECIALIST_SELECTED,
    MULTI_CONTENT_GENERATED,
    VIDEO_VARIANTS_GENERATED,
    LEARNING_RECORDED,
    TREND_FORECASTED,
    GRAPH_UPDATED,
]

# Completed-step → domain event (emitted by BaseAgentHandler on callback)
STEP_TO_DOMAIN_EVENT: dict[str, str] = {
    "trend_intelligence": TREND_INTELLIGENCE_FINISHED,
    "research": RESEARCH_FINISHED,
    "hook": HOOK_FINISHED,
    "script": SCRIPT_FINISHED,
    "script_review": SCRIPT_REVIEW_FINISHED,
    "emotion": EMOTION_FINISHED,
    "content_intelligence": CONTENT_INTELLIGENCE_FINISHED,
    "video_review": VIDEO_REVIEW_FINISHED,
    "storyboard": STORYBOARD_FINISHED,
    "scene_director": SCENE_DIRECTOR_FINISHED,
    "scene": SCENE_CREATED,
    "clip_research": CLIP_RESEARCH_FINISHED,
    "asset_collector": ASSETS_READY,
    "asset_index": ASSET_INDEX_FINISHED,
    "takes": TAKES_FINISHED,
    "voice": VOICE_GENERATED,
    "subtitle": SUBTITLE_CREATED,
    "editor": EDITOR_FINISHED,
    "quality": QUALITY_APPROVED,
    "publisher": PUBLISHER_FINISHED,
    "multi_content": MULTI_CONTENT_GENERATED,
    "multi_content_video": VIDEO_VARIANTS_GENERATED,
    "thumbnail": THUMBNAIL_CREATED,
    "analytics": ANALYTICS_PROCESSED,
    "learning": LEARNING_RECORDED,
}

# V3 mission PascalCase → wire format (documentation / UI labels)
PASCAL_CASE_ALIASES: dict[str, str] = {
    "TrendIntelligenceFinished": TREND_INTELLIGENCE_FINISHED,
    "ResearchFinished": RESEARCH_FINISHED,
    "HookFinished": HOOK_FINISHED,
    "ScriptFinished": SCRIPT_FINISHED,
    "ScriptReviewFinished": SCRIPT_REVIEW_FINISHED,
    "EmotionFinished": EMOTION_FINISHED,
    "VideoReviewFinished": VIDEO_REVIEW_FINISHED,
    "StoryboardFinished": STORYBOARD_FINISHED,
    "SceneDirectorFinished": SCENE_DIRECTOR_FINISHED,
    "ContentIntelligenceFinished": CONTENT_INTELLIGENCE_FINISHED,
    "ReuseSuggested": REUSE_SUGGESTED,
    "AbVariantSelected": AB_VARIANT_SELECTED,
    "ContentScoreComputed": CONTENT_SCORE_COMPUTED,
    "SpecialistSelected": SPECIALIST_SELECTED,
    "MultiContentGenerated": MULTI_CONTENT_GENERATED,
    "VideoVariantsGenerated": VIDEO_VARIANTS_GENERATED,
    "LearningRecorded": LEARNING_RECORDED,
    "TrendForecasted": TREND_FORECASTED,
    "GraphUpdated": GRAPH_UPDATED,
    "SceneFinished": SCENE_CREATED,
    "SceneCreated": SCENE_CREATED,
    "AssetsReady": ASSETS_READY,
    "ClipResearchFinished": CLIP_RESEARCH_FINISHED,
    "AssetIndexFinished": ASSET_INDEX_FINISHED,
    "TakesFinished": TAKES_FINISHED,
    "VoiceReady": VOICE_GENERATED,
    "VoiceGenerated": VOICE_GENERATED,
    "SubtitleReady": SUBTITLE_CREATED,
    "SubtitleCreated": SUBTITLE_CREATED,
    "RenderReady": EDITOR_FINISHED,
    "EditorFinished": EDITOR_FINISHED,
    "QualityApproved": QUALITY_APPROVED,
    "QualityRejected": QUALITY_REJECTED,
    "PublisherFinished": PUBLISHER_FINISHED,
    "AnalyticsFinished": ANALYTICS_PROCESSED,
    "AnalyticsProcessed": ANALYTICS_PROCESSED,
    "ThumbnailCreated": THUMBNAIL_CREATED,
}

# Prefer mission-primary labels for UI
WIRE_TO_PASCAL: dict[str, str] = {
    TREND_INTELLIGENCE_FINISHED: "TrendIntelligenceFinished",
    RESEARCH_FINISHED: "ResearchFinished",
    HOOK_FINISHED: "HookFinished",
    SCRIPT_FINISHED: "ScriptFinished",
    SCRIPT_REVIEW_FINISHED: "ScriptReviewFinished",
    EMOTION_FINISHED: "EmotionFinished",
    VIDEO_REVIEW_FINISHED: "VideoReviewFinished",
    STORYBOARD_FINISHED: "StoryboardFinished",
    SCENE_DIRECTOR_FINISHED: "SceneDirectorFinished",
    CONTENT_INTELLIGENCE_FINISHED: "ContentIntelligenceFinished",
    REUSE_SUGGESTED: "ReuseSuggested",
    AB_VARIANT_SELECTED: "AbVariantSelected",
    CONTENT_SCORE_COMPUTED: "ContentScoreComputed",
    SPECIALIST_SELECTED: "SpecialistSelected",
    MULTI_CONTENT_GENERATED: "MultiContentGenerated",
    VIDEO_VARIANTS_GENERATED: "VideoVariantsGenerated",
    LEARNING_RECORDED: "LearningRecorded",
    TREND_FORECASTED: "TrendForecasted",
    GRAPH_UPDATED: "GraphUpdated",
    SCENE_CREATED: "SceneFinished",
    ASSETS_READY: "AssetsReady",
    CLIP_RESEARCH_FINISHED: "ClipResearchFinished",
    ASSET_INDEX_FINISHED: "AssetIndexFinished",
    TAKES_FINISHED: "TakesFinished",
    VOICE_GENERATED: "VoiceReady",
    SUBTITLE_CREATED: "SubtitleReady",
    EDITOR_FINISHED: "RenderReady",
    QUALITY_APPROVED: "QualityApproved",
    QUALITY_REJECTED: "QualityRejected",
    PUBLISHER_FINISHED: "PublisherFinished",
    ANALYTICS_PROCESSED: "AnalyticsFinished",
    THUMBNAIL_CREATED: "ThumbnailCreated",
}


def resolve_event_type(name: str) -> str:
    """Accept wire format or PascalCase alias; return wire format."""
    if name in ALL_TYPES:
        return name
    return PASCAL_CASE_ALIASES.get(name, name)


def pascal_alias(wire_type: str) -> str:
    """Return PascalCase display name for a wire event type."""
    return WIRE_TO_PASCAL.get(wire_type, wire_type)
