"""Factory-line map for the complete ContentOS production flow.

This module is intentionally descriptive: it gives product, dashboard, docs,
and workflow code one shared vocabulary for the full assembly line.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from contentos_shared.enums import PipelineStep

FactoryStatus = Literal["ready", "partial", "planned"]


@dataclass(frozen=True)
class FactoryModule:
    key: str
    title: str
    description: str
    responsibilities: tuple[str, ...]


@dataclass(frozen=True)
class FactoryStage:
    order: int
    key: str
    title: str
    module: str
    status: FactoryStatus
    pipeline_step: PipelineStep | None = None
    implementation: str | None = None
    next_actions: tuple[str, ...] = ()

    @property
    def executable(self) -> bool:
        return self.pipeline_step is not None and self.status in {"ready", "partial"}


FACTORY_MODULES: tuple[FactoryModule, ...] = (
    FactoryModule(
        key="project",
        title="Projeto e briefing",
        description="Entrada do canal, tema, nicho e contexto editorial.",
        responsibilities=("projetos", "briefing", "workflow escolhido", "contexto da organização"),
    ),
    FactoryModule(
        key="creative",
        title="Criação criativa",
        description="Pesquisa, gancho, roteiro, revisão, cenas, storyboard e direção.",
        responsibilities=("pesquisa", "roteiro", "retenção", "storyboard", "plano de cenas"),
    ),
    FactoryModule(
        key="assets",
        title="Assets e biblioteca",
        description="Descoberta, coleta, análise, indexação, busca e seleção dos melhores takes.",
        responsibilities=("fontes autorizadas", "downloads permitidos", "deduplicação", "tags", "busca"),
    ),
    FactoryModule(
        key="production",
        title="Produção audiovisual",
        description="Narração, legendas, edição, renderização e thumbnail.",
        responsibilities=("voz", "legendas", "ffmpeg", "thumbnail", "render final"),
    ),
    FactoryModule(
        key="quality",
        title="Qualidade e retry",
        description="Validação técnica, retenção, revisão criativa, score e nova tentativa quando necessário.",
        responsibilities=("qa técnico", "retenção", "revisão humana simulada", "auto retry", "content score"),
    ),
    FactoryModule(
        key="intelligence",
        title="Inteligência e memória",
        description="Tendências, potencial viral, aprendizado, base de conhecimento e analytics.",
        responsibilities=("trend", "viral", "learning", "knowledge base", "analytics", "memória criativa"),
    ),
    FactoryModule(
        key="publishing",
        title="Publicação",
        description="SEO, preparação, dry-run e publicação em plataformas conectadas.",
        responsibilities=("metadados", "SEO", "OAuth", "plugins", "publicação", "relatórios"),
    ),
    FactoryModule(
        key="dashboard",
        title="Dashboard",
        description="Acompanhamento em tempo real da linha de montagem.",
        responsibilities=("status", "filas", "custos", "métricas", "operação"),
    ),
)


FACTORY_LINE: tuple[FactoryStage, ...] = (
    FactoryStage(1, "project", "Criar projeto", "project", "ready", implementation="apps/backend projects API"),
    FactoryStage(2, "theme", "Informar tema", "project", "ready", implementation="project pipeline request"),
    FactoryStage(3, "research", "Research Agent", "creative", "ready", PipelineStep.RESEARCH),
    FactoryStage(4, "trend_intelligence", "Trend Intelligence", "intelligence", "ready", PipelineStep.TREND_INTELLIGENCE),
    FactoryStage(5, "hook", "Hook Generator", "creative", "ready", PipelineStep.HOOK),
    FactoryStage(6, "script", "Script Agent", "creative", "ready", PipelineStep.SCRIPT),
    FactoryStage(7, "script_review", "Script Reviewer", "creative", "ready", PipelineStep.SCRIPT_REVIEW),
    FactoryStage(8, "scene", "Scene Planner", "creative", "ready", PipelineStep.SCENE),
    FactoryStage(9, "storyboard", "Storyboard AI", "creative", "ready", PipelineStep.STORYBOARD),
    FactoryStage(10, "scene_director", "Scene Director", "creative", "ready", PipelineStep.SCENE_DIRECTOR),
    FactoryStage(
        11,
        "media_collector",
        "Media Collector (externo)",
        "assets",
        "planned",
        implementation="Programa Media Collector → POST /api/v1/assets/takes/upload",
    ),
    FactoryStage(12, "asset_manager", "Asset Manager", "assets", "ready", PipelineStep.ASSET_INDEX),
    FactoryStage(
        13,
        "media_analyze",
        "Media Analyze",
        "assets",
        "ready",
        PipelineStep.MEDIA_ANALYZE,
        implementation="MediaAnalyzeAgentHandler + media profiles",
    ),
    FactoryStage(
        14,
        "asset_search",
        "Asset Search",
        "assets",
        "ready",
        PipelineStep.ASSET_SEARCH,
        implementation="AssetSearchAgentHandler",
    ),
    FactoryStage(15, "takes", "Takes Manager", "assets", "ready", PipelineStep.TAKES),
    FactoryStage(16, "voice", "Voice Agent", "production", "ready", PipelineStep.VOICE),
    FactoryStage(17, "subtitle", "Subtitle Agent", "production", "ready", PipelineStep.SUBTITLE),
    FactoryStage(18, "editor", "Editor AI", "production", "ready", PipelineStep.EDITOR),
    FactoryStage(19, "thumbnail", "Thumbnail AI", "production", "partial", PipelineStep.THUMBNAIL),
    FactoryStage(20, "quality", "Quality AI", "quality", "ready", PipelineStep.QUALITY),
    FactoryStage(
        21,
        "retention",
        "Retention Engine",
        "quality",
        "ready",
        PipelineStep.RETENTION,
        implementation="RetentionAgentHandler (post-render)",
    ),
    FactoryStage(22, "video_review", "Video Reviewer", "quality", "ready", PipelineStep.VIDEO_REVIEW),
    FactoryStage(
        23,
        "auto_retry",
        "Auto Retry",
        "quality",
        "ready",
        PipelineStep.AUTO_RETRY,
        implementation="AutoRetryAgentHandler + WorkflowEngine rewind policy",
    ),
    FactoryStage(
        24,
        "content_score",
        "Content Score",
        "quality",
        "ready",
        PipelineStep.CONTENT_SCORE,
        implementation="ContentScoreAgentHandler",
    ),
    FactoryStage(
        25,
        "ai_director",
        "AI Director",
        "quality",
        "ready",
        PipelineStep.AI_DIRECTOR,
        implementation="AIDirectorAgentHandler + partial retry plan",
    ),
    FactoryStage(26, "viral_intelligence", "Viral Intelligence", "intelligence", "ready", PipelineStep.CONTENT_INTELLIGENCE),
    FactoryStage(27, "learning", "Learning Engine", "intelligence", "ready", PipelineStep.LEARNING),
    FactoryStage(
        28,
        "knowledge_base",
        "Knowledge Base",
        "intelligence",
        "ready",
        PipelineStep.KNOWLEDGE_BASE,
        implementation="KnowledgeBaseAgentHandler + KnowledgeIndexer",
    ),
    FactoryStage(
        29,
        "creative_memory",
        "Creative Memory",
        "intelligence",
        "ready",
        PipelineStep.CREATIVE_MEMORY,
        implementation="CreativeMemoryAgentHandler",
    ),
    FactoryStage(30, "analytics", "Analytics", "intelligence", "ready", PipelineStep.ANALYTICS),
    FactoryStage(31, "seo", "SEO Engine", "publishing", "ready", PipelineStep.SEO),
    FactoryStage(32, "publisher", "Publisher", "publishing", "partial", PipelineStep.PUBLISHER),
    FactoryStage(33, "dashboard", "Dashboard", "dashboard", "ready", implementation="apps/dashboard"),
)


def list_factory_modules() -> list[FactoryModule]:
    return list(FACTORY_MODULES)


def list_factory_stages() -> list[FactoryStage]:
    return list(FACTORY_LINE)


def executable_factory_steps() -> list[PipelineStep]:
    return [stage.pipeline_step for stage in FACTORY_LINE if stage.pipeline_step is not None]


def stages_by_module(module: str) -> list[FactoryStage]:
    return [stage for stage in FACTORY_LINE if stage.module == module]


def stages_by_status(status: FactoryStatus) -> list[FactoryStage]:
    return [stage for stage in FACTORY_LINE if stage.status == status]


def planned_or_partial_stages() -> list[FactoryStage]:
    return [stage for stage in FACTORY_LINE if stage.status in {"partial", "planned"}]
