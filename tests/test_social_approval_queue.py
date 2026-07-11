from contentos_growth.application.social_approval_queue import build_social_approval_queue
from contentos_growth.application.social_autopilot import build_social_autopilot_plan


def test_social_approval_queue_marks_assisted_items_for_review() -> None:
    plan = build_social_autopilot_plan(
        project_id="project-1",
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

    assert queue.status == "review_required"
    assert queue.items
    assert queue.items[0].status == "needs_review"
    assert queue.items[0].publisher_payload is not None
    assert queue.items[0].publisher_payload["requires_manual_approval"] is True
    assert queue.items[0].scheduler_payload["action"] == "schedule_review"


def test_social_approval_queue_blocks_governance_failures() -> None:
    plan = build_social_autopilot_plan(
        project_id="project-1",
        mode="live",
        publish_authorized=False,
        channels=[{"channel_id": "ch-1", "platform": "youtube", "name": "Main", "has_credentials": True}],
        calendar_items=[{"id": "cal-1", "title": "Tema", "metadata": {"platform": "youtube", "content_type": "post"}}],
    )

    queue = build_social_approval_queue(
        project_id="project-1",
        operations=[item.to_dict() for item in [*plan.operations, *plan.blocked_operations]],
        governance_contract=plan.governance_contract,
    )

    assert queue.status == "blocked"
    assert queue.items[0].status == "blocked"
    assert queue.items[0].scheduler_payload is None
    assert queue.items[0].required_actions


def test_social_approval_queue_creates_ready_handoff_for_allowed_items() -> None:
    plan = build_social_autopilot_plan(
        project_id="project-1",
        mode="automatic",
        channels=[{"channel_id": "ch-1", "platform": "youtube", "name": "Main", "has_credentials": True}],
        calendar_items=[{"id": "cal-1", "title": "Tema", "metadata": {"platform": "youtube", "content_type": "post"}}],
    )

    queue = build_social_approval_queue(
        project_id="project-1",
        operations=[item.to_dict() for item in [*plan.operations, *plan.blocked_operations]],
        governance_contract=plan.governance_contract,
    )

    assert queue.status == "ready"
    assert queue.items[0].status == "ready"
    assert queue.items[0].publisher_payload["status"] == "ready"
    assert queue.items[0].scheduler_payload["action"] == "schedule_execution"
    assert queue.publisher_contract["publishes_directly"] is False


