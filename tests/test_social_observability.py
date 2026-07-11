from contentos_growth.application.social_approval_queue import build_social_approval_queue
from contentos_growth.application.social_autopilot import build_social_autopilot_plan
from contentos_growth.application.social_dispatcher import build_social_dispatch_plan
from contentos_growth.application.social_observability import build_social_observability_report


def _build_lifecycle(*, mode: str = "assisted", publish_authorized: bool = False, execute: bool = False):
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
    return plan, queue, dispatch


def test_social_observability_reports_attention_for_assisted_review() -> None:
    plan, queue, dispatch = _build_lifecycle()

    report = build_social_observability_report(
        project_id="project-1",
        plan=plan.to_dict(),
        queue=queue.to_dict(),
        dispatch=dispatch.to_dict(),
    )

    assert report.status == "attention"
    assert report.counts["review_items"] == 1
    assert report.readiness_score < 100
    assert report.manual_actions
    assert report.lifecycle["queue_status"] == "review_required"


def test_social_observability_reports_healthy_for_ready_dispatch() -> None:
    plan, queue, dispatch = _build_lifecycle(mode="automatic", execute=True)

    report = build_social_observability_report(
        project_id="project-1",
        plan=plan.to_dict(),
        queue=queue.to_dict(),
        dispatch=dispatch.to_dict(),
    )

    assert report.status == "healthy"
    assert report.readiness_score == 100
    assert report.counts["dispatch_commands"] == 2
    assert report.lifecycle["dispatch_by_target"] == {"Publisher": 1, "Scheduler": 1}


def test_social_observability_reports_blocked_for_live_without_authorization() -> None:
    plan, queue, dispatch = _build_lifecycle(mode="live", publish_authorized=False, execute=True)

    report = build_social_observability_report(
        project_id="project-1",
        plan=plan.to_dict(),
        queue=queue.to_dict(),
        dispatch=dispatch.to_dict(),
    )

    assert report.status == "blocked"
    assert report.counts["blocked_items"] >= 1
    assert "missing_explicit_authorization" in report.risks
    assert report.readiness_score < 80
    assert report.audit_events
