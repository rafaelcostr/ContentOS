"""IReuseAdvisor adapter — delegates to ReuseAdvisor + IKnowledgeQuery."""

from __future__ import annotations

from contentos_intelligence.application.reuse_advisor import ReuseAdvisor
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.interfaces import IKnowledgeQuery, IReuseAdvisor
from contentos_intelligence.domain.reuse_suggestion import ReuseSuggestion

_default_advisor: ReuseAdvisor | None = None


class DbReuseAdvisor(IReuseAdvisor):
    """Registry-facing adapter wrapping ReuseAdvisor."""

    def __init__(self, knowledge_query: IKnowledgeQuery) -> None:
        self._inner = ReuseAdvisor(knowledge_query)

    async def suggest(self, context: IntelligenceContext) -> list[ReuseSuggestion]:
        return await self._inner.suggest(context)

    def invalidate_cache(self, project_id=None) -> None:
        self._inner.invalidate_cache(project_id)


def get_reuse_advisor(knowledge_query: IKnowledgeQuery) -> ReuseAdvisor:
    return ReuseAdvisor(knowledge_query)
