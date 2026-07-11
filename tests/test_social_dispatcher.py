from contentos_growth.application.social_approval_queue import build_social_approval_queue
from contentos_growth.application.social_autopilot import build_social_autopilot_plan
from contentos_growth.application.social_dispatcher import build_social_dispatch_plan


def test_social_dispatcher_prepares_ready_publisher_and_scheduler_commands() -> None:
    plan = build_social_autopilot_plan(
        project_id="project-1",
        mode="automatic",
        channels=[{"channel_id": "ch-1", "platform": "youtube", "name": "Main", "has_credentials": True}],
        calendar_items=[{"id": "cal-1", "title": "Tema", "metadata": {"platform": "youtube", "content_type": "post"}}],
    )
    queue = build_social_approval_queue(
        project_id="project-1",
        operations=[item.to_dict() for item in plan.operations],
        governance_contract=plan.governance_contract,
    )

    dispatch = build_social_dispatch_plan(
        project_id="project-1",
        queue_items=[item.to_dict() for item in queue.items],
        execute=True,
        actor_id="user-1",
    )

    targets = {command.target for command in dispatch.commands}
    assert dispatch.status == "prepared"
    assert targets == {"Publisher", "Scheduler"}
    assert all(command.dry_run is False for command in dispatch.commands)
    assert dispatch.commands[0].audit_event["actor_id"] == "user-1"
    assert dispatch.execution_contract["publishes_directly"] is False


def test_social_dispatcher_skips_review_items_by_default() -> None:
    plan = build_social_autopilot_plan(
        project_id="project-1",
        channels=[{"channel_id": "ch-1", "platform": "youtube", "name": "Main", "has_credentials": True}],
        calendar_items=[{"id": "cal-1", "title": "Tema", "metadata": {"platform": "youtube", "content_type": "post"}}],
    )
    queue = build_social_approval_queue(
        project_id="project-1",
        operations=[item.to_dict() for item in plan.operations],
        governance_contract=plan.governance_contract,
    )

    dispatch = build_social_dispatch_plan(
        project_id="project-1",
        queue_items=[item.to_dict() for item in queue.items],
    )

    assert dispatch.status == "blocked"
    assert not dispatch.commands
    assert dispatch.skipped_items[0]["status"] == "needs_review"


def test_social_dispatcher_keeps_review_items_dry_run_when_allowed() -> None:
    plan = build_social_autopilot_plan(
        project_id="project-1",
        channels=[{"channel_id": "ch-1", "platform": "youtube", "name": "Main", "has_credentials": True}],
        calendar_items=[{"id": "cal-1", "title": "Tema", "metadata": {"platform": "youtube", "content_type": "post"}}],
    )
    queue = build_social_approval_queue(
        project_id="project-1",
        operations=[item.to_dict() for item in plan.operations],
        governance_contract=plan.governance_contract,
    )

    dispatch = build_social_dispatch_plan(
        project_id="project-1",
        queue_items=[item.to_dict() for item in queue.items],
        execute=True,
        allow_review_items=True,
    )

    assert dispatch.status == "prepared"
    assert dispatch.commands
    assert all(command.dry_run is True for command in dispatch.commands)


def test_social_dispatcher_blocks_governance_blocked_items() -> None:
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

    dispatch = build_social_dispatch_plan(
        project_id="project-1",
        queue_items=[item.to_dict() for item in queue.items],
        execute=True,
    )

    assert dispatch.status == "blocked"
    assert not dispatch.commands
    assert dispatch.skipped_items[0]["status"] == "blocked"
