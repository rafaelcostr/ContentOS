from contentos_growth.application.social_approval_queue import build_social_approval_queue
from contentos_growth.application.social_autopilot import build_social_autopilot_plan
from contentos_growth.application.social_dispatcher import build_social_dispatch_plan
from contentos_growth.application.social_learning import build_social_learning_report
from contentos_growth.application.social_observability import build_social_observability_report


def _observability(*, mode: str = "assisted", publish_authorized: bool = False, execute: bool = False):
    plan = build_social_autopilot_plan(
        project_id="project-1",
        mode=mode,
        publish_authorized=publish_authorized,
        channels=[{"channel_id": "ch-1", "platform": "youtube", "name": "Main", "has_credentials": True}],
        calendar_items=[{"id": "cal-1", "title": "Tema", "metadata": {"platform": "youtube", "content_type": "post"}}],
        actor_id="user-1",
    )
    queue = build_social_approval_queue(
        project_id="project-1",
        operations=[item.to_dict() for item in [*plan.operations, *plan.blocked_operations]],
        governance_contract=plan.governance_contract,
        actor_id="user-1",
    )
    dispatch = build_social_dispatch_plan(
        project_id="project-1",
        queue_items=[item.to_dict() for item in queue.items],
        execute=execute,
        actor_id="user-1",
    )
    return build_social_observability_report(
        project_id="project-1",
        plan=plan.to_dict(),
        queue=queue.to_dict(),
        dispatch=dispatch.to_dict(),
    )


def test_social_learning_recommends_manual_review_for_attention() -> None:
    observability = _observability()

    report = build_social_learning_report(project_id="project-1", observability=observability.to_dict())

    assert report.status == "learning"
    assert report.recommendations
    assert report.next_cycle["review_queue"] is True
    assert any(item.action == "manual_review" for item in report.recommendations)


def test_social_learning_blocks_when_governance_blocks() -> None:
    observability = _observability(mode="live", publish_authorized=False, execute=True)

    report = build_social_learning_report(project_id="project-1", observability=observability.to_dict())

    assert report.status == "blocked"
    assert "missing_explicit_authorization" in report.blockers
    assert report.next_cycle["resolve_blockers"] >= 1
    assert any(item.action == "resolve_social_risk" for item in report.recommendations)


def test_social_learning_captures_winning_memory_candidates() -> None:
    observability = _observability(mode="automatic", execute=True)

    report = build_social_learning_report(
        project_id="project-1",
        observability=observability.to_dict(),
        performance_rows=[{"platform": "youtube", "title": "Hook vencedor", "performance_tier": "high"}],
        community_signals={"video_ideas": [{"title": "Pedido da comunidade", "priority": "high"}]},
    )

    assert report.status == "ready"
    assert report.memory_candidates
    assert report.next_cycle["update_memory"] is True
    assert any(item.action == "add_to_social_calendar" for item in report.recommendations)
    assert any("Hook vencedor" in item for item in report.learned)
