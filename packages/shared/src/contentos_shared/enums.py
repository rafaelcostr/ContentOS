import enum


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class PipelineStep(str, enum.Enum):
    RESEARCH = "research"
    SCRIPT = "script"
    SCENE = "scene"
    TAKES = "takes"
    VOICE = "voice"
    SUBTITLE = "subtitle"
    EDITOR = "editor"
    QUALITY = "quality"
    PUBLISHER = "publisher"
    # V2 pipeline extensions (external download owned by Media Collector)
    ASSET_INDEX = "asset_index"
    MEDIA_ANALYZE = "media_analyze"
    ASSET_SEARCH = "asset_search"
    THUMBNAIL = "thumbnail"
    ANALYTICS = "analytics"
    # V3 creative agents
    TREND_INTELLIGENCE = "trend_intelligence"
    HOOK = "hook"
    SCRIPT_REVIEW = "script_review"
    EMOTION = "emotion"
    VIDEO_REVIEW = "video_review"
    STORYBOARD = "storyboard"
    SCENE_DIRECTOR = "scene_director"
    AUTO_RETRY = "auto_retry"
    # V4 intelligence
    CONTENT_INTELLIGENCE = "content_intelligence"
    CONTENT_SCORE = "content_score"
    MULTI_CONTENT = "multi_content"
    MULTI_CONTENT_VIDEO = "multi_content_video"
    LEARNING = "learning"
    KNOWLEDGE_BASE = "knowledge_base"
    RETENTION = "retention"
    SEO = "seo"
    AI_DIRECTOR = "ai_director"
    CREATIVE_MEMORY = "creative_memory"

    @classmethod
    def ordered(cls) -> list["PipelineStep"]:
        """V1 core pipeline — 9 steps."""
        return [
            cls.RESEARCH,
            cls.SCRIPT,
            cls.SCENE,
            cls.TAKES,
            cls.VOICE,
            cls.SUBTITLE,
            cls.EDITOR,
            cls.QUALITY,
            cls.PUBLISHER,
        ]

    @classmethod
    def _insert_media_analyze(cls, steps: list["PipelineStep"]) -> list["PipelineStep"]:
        if cls.MEDIA_ANALYZE in steps:
            return steps
        out = list(steps)
        if cls.ASSET_INDEX in out:
            out.insert(out.index(cls.ASSET_INDEX) + 1, cls.MEDIA_ANALYZE)
        return out

    @classmethod
    def v2_ordered(cls) -> list["PipelineStep"]:
        """Full V2 pipeline — library match + media_analyze (no external download)."""
        return cls._insert_media_analyze(
            [
            cls.RESEARCH,
            cls.SCRIPT,
            cls.SCENE,
            cls.ASSET_INDEX,
            cls.ASSET_SEARCH,
            cls.TAKES,
            cls.VOICE,
            cls.SUBTITLE,
            cls.EDITOR,
            cls.QUALITY,
            cls.PUBLISHER,
            cls.THUMBNAIL,
            cls.ANALYTICS,
            ]
        )

    @classmethod
    def v3_quality_ordered(cls) -> list["PipelineStep"]:
        """V3 quality pipeline — creative agents + storyboard + video review."""
        return [
            cls.TREND_INTELLIGENCE,
            cls.RESEARCH,
            cls.HOOK,
            cls.SCRIPT,
            cls.SCRIPT_REVIEW,
            cls.EMOTION,
            cls.SCENE,
            cls.STORYBOARD,
            cls.SCENE_DIRECTOR,
            cls.TAKES,
            cls.VOICE,
            cls.SUBTITLE,
            cls.EDITOR,
            cls.QUALITY,
            cls.VIDEO_REVIEW,
            cls.PUBLISHER,
        ]

    @classmethod
    def v4_intelligence_ordered(cls) -> list["PipelineStep"]:
        """V4 pipeline — v3-quality + content_intelligence after emotion."""
        steps = list(cls.v3_quality_ordered())
        insert_at = steps.index(cls.EMOTION) + 1
        steps.insert(insert_at, cls.CONTENT_INTELLIGENCE)
        return steps

    @classmethod
    def v4_multi_text_ordered(cls) -> list["PipelineStep"]:
        """V4.2.1 — v4-intelligence + multi_content after publisher."""
        steps = list(cls.v4_intelligence_ordered())
        pub_idx = steps.index(cls.PUBLISHER)
        steps.insert(pub_idx + 1, cls.MULTI_CONTENT)
        return steps

    @classmethod
    def v4_multi_full_ordered(cls) -> list["PipelineStep"]:
        """V4.2.2 — v4-multi-text + multi_content_video after multi_content."""
        steps = list(cls.v4_multi_text_ordered())
        steps.append(cls.MULTI_CONTENT_VIDEO)
        return steps

    @classmethod
    def factory_full_ordered(cls) -> list["PipelineStep"]:
        """Full factory line using only executable agent steps.

        Uses executable handlers for the complete factory line.
        """
        return cls._insert_media_analyze(
            [
            cls.RESEARCH,
            cls.TREND_INTELLIGENCE,
            cls.HOOK,
            cls.SCRIPT,
            cls.SCRIPT_REVIEW,
            cls.SCENE,
            cls.STORYBOARD,
            cls.SCENE_DIRECTOR,
            cls.ASSET_INDEX,
            cls.ASSET_SEARCH,
            cls.TAKES,
            cls.VOICE,
            cls.SUBTITLE,
            cls.EDITOR,
            cls.THUMBNAIL,
            cls.QUALITY,
            cls.RETENTION,
            cls.VIDEO_REVIEW,
            cls.AUTO_RETRY,
            cls.CONTENT_SCORE,
            cls.AI_DIRECTOR,
            cls.CONTENT_INTELLIGENCE,
            cls.LEARNING,
            cls.KNOWLEDGE_BASE,
            cls.CREATIVE_MEMORY,
            cls.ANALYTICS,
            cls.SEO,
            cls.PUBLISHER,
            ]
        )

    @classmethod
    def v5_media_autopilot_ordered(cls) -> list["PipelineStep"]:
        """V5 media autopilot — tema → biblioteca (Media Collector) → take → MP4."""
        return cls._insert_media_analyze(
            [
                cls.RESEARCH,
                cls.SCRIPT,
                cls.SCENE,
                cls.ASSET_INDEX,
                cls.ASSET_SEARCH,
                cls.TAKES,
                cls.VOICE,
                cls.SUBTITLE,
                cls.EDITOR,
                cls.QUALITY,
                cls.RETENTION,
                cls.AI_DIRECTOR,
                cls.SEO,
                cls.CREATIVE_MEMORY,
                cls.PUBLISHER,
            ]
        )


class AsyncAgentStep(str, enum.Enum):
    """V2 async agents — outside the V1 9-step pipeline."""

    THUMBNAIL = "thumbnail"
    ANALYTICS = "analytics"
    LEARNING = "learning"


class PipelineStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssetCategory(str, enum.Enum):
    ASSETS = "assets"
    TAKES = "takes"
    AUDIO = "audio"
    SCRIPTS = "scripts"
    VIDEOS = "videos"
    RENDERS = "renders"
    IMAGES = "images"
    THUMBS = "thumbs"
    CAPTIONS = "captions"
    TEMP = "temp"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
