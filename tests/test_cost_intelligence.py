from contentos_autopilot.cost import build_cost_decision_score
from contentos_growth.application.content_factory_bridge import build_growth_context_json


def test_cost_decision_blocks_when_credits_are_low() -> None:
    decision = build_cost_decision_score(
        quantity=3,
        credit_cost_per_pipeline=2,
        credits_balance=2,
        monthly_quota=20,
        monthly_used=5,
        concurrent_limit=5,
        concurrent_active=0,
    )

    data = decision.to_dict()
    assert data["status"] == "blocked"
    assert data["credits_ok"] is False
    assert data["total_credit_cost"] == 6
    assert data["blockers"]


def test_cost_decision_requires_approval_for_expensive_ai_media() -> None:
    decision = build_cost_decision_score(
        quantity=1,
        credit_cost_per_pipeline=1,
        credits_balance=50,
        media_strategy={"source_mix": [{"source": "ai_video", "percentage": 80}]},
        require_manual_approval_above=10,
    )

    data = decision.to_dict()
    assert data["status"] == "approval_required"
    assert data["mode"] == "economy"
    assert data["estimated_ai_cost_units"] >= 10


def test_growth_context_passes_cost_decision_to_factory() -> None:
    cost_decision = build_cost_decision_score(quantity=1, credit_cost_per_pipeline=1).to_dict()
    context = build_growth_context_json(
        calendar_item={
            "project_id": "project-1",
            "channel_id": "channel-1",
            "title": "carros de luxo",
            "metadata": {
                "platform": "tiktok",
                "content_type": "reel",
                "cost_decision": cost_decision,
            },
        }
    )

    assert context["cost_decision"]["status"] == "ready"
    assert context["cost_decision"]["guardrails"]
