"""Tests for Multi Content text (V4.2.1 / Epic 2a)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_events.domain.event_types import ALL_TYPES, MULTI_CONTENT_GENERATED, resolve_event_type
from contentos_intelligence.application.multi_content import MultiContentService
from contentos_intelligence.application.multi_content.heuristics import GENERATORS, generate_thread_x
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.multi_content import TEXT_FORMATS
from contentos_shared.enums import PipelineStep
from contentos_shared.workflow_templates import BUILTIN_TEMPLATES, get_builtin, list_builtin_names


def test_text_formats_complete():
    assert TEXT_FORMATS == frozenset(
        {"thread_x", "linkedin_post", "newsletter", "seo_article", "email_marketing"}
    )
    assert set(GENERATORS.keys()) == set(TEXT_FORMATS)


def test_thread_x_heuristic_from_script():
    artifact = generate_thread_x(
        {
            "topic": "GTA 6",
            "script": {
                "title": "GTA 6 revelado",
                "full_text": "Ninguém esperava isso. O mapa é gigante. A Rockstar surpreendeu todos.",
            },
        }
    )
    assert artifact.format == "thread_x"
    assert len(artifact.data.get("posts", [])) >= 1
    assert artifact.content


def test_multi_content_service_generates_all_formats():
    service = MultiContentService()
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="IA no trabalho",
        payload={
            "script": {
                "title": "ChatGPT na empresa",
                "full_text": "A IA mudou o marketing. Empresas que não adaptam perdem mercado.",
                "call_to_action": "Comenta como você usa IA",
            }
        },
    )
    report = service.generate(ctx)
    assert len(report.artifacts) == 5
    formats = {a.format for a in report.artifacts}
    assert formats == set(TEXT_FORMATS)


def test_v4_multi_text_template():
    assert "v4-multi-text" in BUILTIN_TEMPLATES
    tpl = get_builtin("v4-multi-text")
    assert tpl is not None
    steps = tpl["steps"]
    assert steps[-2] == "publisher"
    assert steps[-1] == "multi_content"
    assert steps.index("content_intelligence") == steps.index("emotion") + 1
    assert len(steps) == 18


def test_v4_multi_text_ordered_enum():
    steps = [s.value for s in PipelineStep.v4_multi_text_ordered()]
    assert steps[-1] == "multi_content"


def test_list_builtin_includes_v4_multi_text():
    assert "v4-multi-text" in list_builtin_names()


def test_multi_content_generated_event_registered():
    assert MULTI_CONTENT_GENERATED in ALL_TYPES
    assert resolve_event_type("MultiContentGenerated") == MULTI_CONTENT_GENERATED
