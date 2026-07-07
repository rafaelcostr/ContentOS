"""Tests for Event Bus (V2.7 / Tier A1)."""

from uuid import uuid4

from contentos_events.application.publisher import EventBusPublisher
from contentos_events.domain.event import DomainEvent
from contentos_events.domain.event_types import (
    ASSET_INDEX_FINISHED,
    ASSET_SEARCH_FINISHED,
    ASSETS_READY,
    AUTO_RETRY_FINISHED,
    CLIP_RESEARCH_FINISHED,
    KNOWLEDGE_BASE_INDEXED,
    MEDIA_ANALYZE_FINISHED,
    QUALITY_REJECTED,
    RESEARCH_FINISHED,
    SCRIPT_FINISHED,
    STEP_STARTED,
    STEP_TO_DOMAIN_EVENT,
    TAKES_FINISHED,
    pascal_alias,
    resolve_event_type,
)
from contentos_shared.enums import PipelineStep
from contentos_shared.events import WorkflowEvent


class FakeTransport:
    def __init__(self) -> None:
        self.stream: list[dict] = []
        self.legacy: list[dict] = []

    async def append(self, payload: dict) -> str:
        self.stream.append(payload)
        return "1-0"

    def append_sync(self, payload: dict) -> str:
        self.stream.append(payload)
        return "1-0"

    async def publish_legacy(self, payload: dict) -> None:
        self.legacy.append(payload)

    def publish_legacy_sync(self, payload: dict) -> None:
        self.legacy.append(payload)

    async def stream_info(self) -> dict:
        return {"stream_key": "test", "length": len(self.stream)}


def test_domain_event_to_dict():
    pid = uuid4()
    event = DomainEvent(
        event_type=RESEARCH_FINISHED,
        pipeline_id=pid,
        step="research",
        agent="research",
        status="completed",
        payload={"topics": 3},
    )
    data = event.to_dict()
    assert data["type"] == RESEARCH_FINISHED
    assert data["pipeline_id"] == str(pid)
    assert data["data"]["topics"] == 3


def test_from_workflow_event():
    pid = uuid4()
    wf = WorkflowEvent(type=STEP_STARTED, pipeline_id=pid, step="script", status="running")
    domain = DomainEvent.from_workflow_event(wf)
    assert domain.event_type == STEP_STARTED
    assert domain.pipeline_id == pid
    assert domain.step == "script"


def test_from_agent_callback_completed():
    pid = uuid4()
    proj = uuid4()
    jid = uuid4()
    event = DomainEvent.from_agent_callback(
        step="script",
        project_id=proj,
        pipeline_id=pid,
        job_id=jid,
        status="completed",
    )
    assert event.event_type == SCRIPT_FINISHED
    assert event.project_id == proj


def test_from_agent_callback_failed():
    event = DomainEvent.from_agent_callback(
        step="research",
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        status="failed",
        payload={"error": "timeout"},
    )
    assert event.event_type == "step.failed"
    assert event.payload["error"] == "timeout"


def test_from_agent_callback_quality_failed():
    event = DomainEvent.from_agent_callback(
        step="quality",
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        status="failed",
    )
    assert event.event_type == QUALITY_REJECTED


def test_v2_steps_map_to_domain_events():
    expected = {
        "clip_research": CLIP_RESEARCH_FINISHED,
        "asset_collector": ASSETS_READY,
        "asset_index": ASSET_INDEX_FINISHED,
        "media_analyze": MEDIA_ANALYZE_FINISHED,
        "asset_search": ASSET_SEARCH_FINISHED,
        "takes": TAKES_FINISHED,
    }
    for step, event_type in expected.items():
        event = DomainEvent.from_agent_callback(
            step=step,
            project_id=uuid4(),
            pipeline_id=uuid4(),
            job_id=uuid4(),
            status="completed",
        )
        assert event.event_type == event_type


def test_v2_dynamic_steps_all_have_domain_events():
    for step in PipelineStep.v2_ordered():
        assert step.value in STEP_TO_DOMAIN_EVENT, f"missing domain event for {step.value}"


def test_pascal_aliases_resolve_to_wire_format():
    assert resolve_event_type("AssetsReady") == ASSETS_READY
    assert resolve_event_type("AutoRetryFinished") == AUTO_RETRY_FINISHED
    assert resolve_event_type("KnowledgeBaseIndexed") == KNOWLEDGE_BASE_INDEXED
    assert resolve_event_type("AssetSearchFinished") == ASSET_SEARCH_FINISHED
    assert resolve_event_type("ResearchFinished") == RESEARCH_FINISHED
    assert resolve_event_type("RenderReady") == "editor.finished"
    assert resolve_event_type(ASSETS_READY) == ASSETS_READY


def test_pascal_alias_display():
    assert pascal_alias(ASSETS_READY) == "AssetsReady"
    assert pascal_alias(AUTO_RETRY_FINISHED) == "AutoRetryFinished"
    assert pascal_alias(KNOWLEDGE_BASE_INDEXED) == "KnowledgeBaseIndexed"
    assert pascal_alias(CLIP_RESEARCH_FINISHED) == "ClipResearchFinished"
    assert pascal_alias(TAKES_FINISHED) == "TakesFinished"


async def test_publisher_dual_publish(monkeypatch):
    transport = FakeTransport()
    monkeypatch.setattr("contentos_events.application.publisher.store_sync", lambda _p: True)
    publisher = EventBusPublisher(transport=transport)
    wf = WorkflowEvent(type="pipeline.created", pipeline_id=uuid4(), status="pending")
    await publisher.publish(wf)
    assert len(transport.stream) == 1
    assert len(transport.legacy) == 1
    assert transport.stream[0]["type"] == "pipeline.created"


def test_publisher_sync(monkeypatch):
    transport = FakeTransport()
    monkeypatch.setattr("contentos_events.application.publisher.store_sync", lambda _p: True)
    publisher = EventBusPublisher(transport=transport)
    event = DomainEvent(event_type=RESEARCH_FINISHED, step="research", status="completed")
    publisher.publish_sync(event)
    assert transport.stream[0]["type"] == RESEARCH_FINISHED
    assert len(transport.legacy) == 1
