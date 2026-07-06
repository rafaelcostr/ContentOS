"""Unified Celery worker — registers all agent tasks (V1 + V2 async)."""

from contentos_agents.handlers.analytics import AnalyticsAgentHandler
from contentos_agents.handlers.asset_collector import AssetCollectorAgentHandler
from contentos_agents.handlers.asset_index import AssetIndexAgentHandler
from contentos_agents.handlers.clip_research import ClipResearchAgentHandler
from contentos_agents.handlers.content_intelligence import ContentIntelligenceAgentHandler
from contentos_agents.handlers.editor import EditorAgentHandler
from contentos_agents.handlers.emotion import EmotionAgentHandler
from contentos_agents.handlers.hook import HookAgentHandler
from contentos_agents.handlers.learning import LearningAgentHandler
from contentos_agents.handlers.multi_content import MultiContentAgentHandler
from contentos_agents.handlers.multi_content_video import MultiContentVideoAgentHandler
from contentos_agents.handlers.publisher import PublisherAgentHandler
from contentos_agents.handlers.quality import QualityAgentHandler
from contentos_agents.handlers.research import ResearchAgentHandler
from contentos_agents.handlers.scene import SceneAgentHandler
from contentos_agents.handlers.scene_director import SceneDirectorAgentHandler
from contentos_agents.handlers.script import ScriptAgentHandler
from contentos_agents.handlers.script_review import ScriptReviewAgentHandler
from contentos_agents.handlers.storyboard import StoryboardAgentHandler
from contentos_agents.handlers.subtitle import SubtitleAgentHandler
from contentos_agents.handlers.takes import TakesAgentHandler
from contentos_agents.handlers.thumbnail import ThumbnailAgentHandler
from contentos_agents.handlers.trend_intelligence import TrendIntelligenceAgentHandler
from contentos_agents.handlers.video_review import VideoReviewAgentHandler
from contentos_agents.handlers.voice import VoiceAgentHandler
from contentos_intelligence.application.bootstrap import configure_intelligence_registry
from contentos_shared.agents.base import run_async
from contentos_shared.telemetry import init_telemetry
from contentos_workflow.tasks import celery_app


def bootstrap_worker() -> None:
    init_telemetry("contentos-agents-worker")
    configure_intelligence_registry(with_database=False)


bootstrap_worker()

HANDLERS = {
    "trend_intelligence": TrendIntelligenceAgentHandler(),
    "research": ResearchAgentHandler(),
    "hook": HookAgentHandler(),
    "script": ScriptAgentHandler(),
    "script_review": ScriptReviewAgentHandler(),
    "emotion": EmotionAgentHandler(),
    "content_intelligence": ContentIntelligenceAgentHandler(),
    "scene": SceneAgentHandler(),
    "storyboard": StoryboardAgentHandler(),
    "scene_director": SceneDirectorAgentHandler(),
    "takes": TakesAgentHandler(),
    "voice": VoiceAgentHandler(),
    "subtitle": SubtitleAgentHandler(),
    "editor": EditorAgentHandler(),
    "quality": QualityAgentHandler(),
    "video_review": VideoReviewAgentHandler(),
    "publisher": PublisherAgentHandler(),
    "multi_content": MultiContentAgentHandler(),
    "multi_content_video": MultiContentVideoAgentHandler(),
    "clip_research": ClipResearchAgentHandler(),
    "asset_collector": AssetCollectorAgentHandler(),
    "asset_index": AssetIndexAgentHandler(),
    "thumbnail": ThumbnailAgentHandler(),
    "analytics": AnalyticsAgentHandler(),
    "learning": LearningAgentHandler(),
}

ALL_QUEUES = ",".join(f"contentos.{step}" for step in HANDLERS)


def _register(step: str, handler) -> None:
    @celery_app.task(name=f"contentos.{step}.execute", bind=True, max_retries=0)
    def execute(self, **kwargs):
        return run_async(handler.run(**kwargs))


for _step, _handler in HANDLERS.items():
    _register(_step, _handler)
