"""Knowledge Base agent tests."""

from uuid import uuid4

import pytest
from contentos_agents.handlers.knowledge_base import KnowledgeBaseAgentHandler
from contentos_shared.schemas.agent import AgentTaskInput


@pytest.mark.asyncio
async def test_knowledge_base_handler_skips_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    handler = KnowledgeBaseAgentHandler()
    task = AgentTaskInput(
        job_id=uuid4(),
        pipeline_id=uuid4(),
        project_id=uuid4(),
        step="knowledge_base",
        payload={"topic": "Teste"},
    )

    output = await handler.execute(task)

    assert output.status == "completed"
    assert output.data["knowledge_base_skipped"] is True
