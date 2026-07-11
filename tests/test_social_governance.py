from contentos_growth.application.social_autopilot import build_social_autopilot_plan
from contentos_growth.application.social_governance import (
    SocialAutomationPolicy,
    evaluate_social_operation,
    evaluate_social_plan,
)


def test_social_governance_blocks_live_without_authorization() -> None:
    operation = {
        "kind": "thread",
        "title": "Post live",
        "platform": "youtube",
        "channel_id": "channel-1",
        "mode": "live",
        "can_execute": True,
        "execution": {"delegate_to": "Publisher", "publish_mode": "live"},
    }
    policy = SocialAutomationPolicy.from_mapping({"mode": "live"})

    decision = evaluate_social_operation(project_id="project-1", operation=operation, policy=policy)

    assert decision.status == "blocked"
    assert decision.allowed is False
    assert "missing_explicit_authorization" in decision.reasons
    assert decision.audit_event["event"] == "social_governance_decision"


def test_social_governance_requires_allowed_platform() -> None:
    operation = {
        "kind": "story",
        "title": "Story",
        "platform": "unknown-network",
        "mode": "assisted",
        "can_execute": True,
        "execution": {"delegate_to": "Publisher", "publish_mode": "prepare_only"},
    }
    policy = SocialAutomationPolicy.from_mapping({"allowed_platforms": ["youtube"]})

    decision = evaluate_social_operation(project_id="project-1", operation=operation, policy=policy)

    assert decision.status == "blocked"
    assert "platform_not_allowed" in decision.reasons


def test_social_governance_generates_audit_log_for_plan() -> None:
    operations = [
        {
            "kind": "community_post",
            "title": "Pergunta da comunidade",
            "platform": "youtube",
            "mode": "assisted",
            "can_execute": True,
            "execution": {"delegate_to": "Publisher", "publish_mode": "prepare_only"},
        }
    ]
    policy = SocialAutomationPolicy.from_mapping({"mode": "assisted"})

    report = evaluate_social_plan(
        project_id="project-1",
        operations=operations,
        policy=policy,
        actor_id="user-1",
        request_id="req-1",
    )

    assert report.status == "review_required"
    assert len(report.decisions) == 1
    assert report.audit_log[0]["actor_id"] == "user-1"
    assert report.audit_log[0]["request_id"] == "req-1"


def test_social_autopilot_embeds_governance_contract() -> None:
    plan = build_social_autopilot_plan(
        project_id="project-1",
        channels=[{"channel_id": "ch-1", "platform": "youtube", "name": "Main", "has_credentials": True}],
        calendar_items=[
            {
                "id": "cal-1",
                "title": "Tema",
                "metadata": {"platform": "youtube", "content_type": "post"},
            }
        ],
        actor_id="user-1",
    )
    data = plan.to_dict()

    assert data["governance_contract"]["status"] == "review_required"
    assert data["governance_contract"]["policy"]["mode"] == "assisted"
    assert data["audit_log"]
    assert data["audit_log"][0]["actor_id"] == "user-1"
