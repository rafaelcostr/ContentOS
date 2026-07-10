"""Autopilot strategic brain.

The brain ranks context and returns decisions. It never executes actions.
"""

from __future__ import annotations

from contentos_autopilot.domain import (
    AutopilotAction,
    AutopilotContext,
    AutopilotContextProvider,
    AutopilotDecision,
    AutopilotDecisionStatus,
    AutopilotMode,
    utc_now,
)


def _priority_rank(priority: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(priority, 2)


def _decision_status(context: AutopilotContext, actions: list[AutopilotAction]) -> AutopilotDecisionStatus:
    if context.blockers and not actions:
        return "blocked"
    if actions and context.score >= 60:
        return "ready"
    return "partial"


class AutopilotBrain:
    """Pure decision layer for Autonomous Creator OS."""

    def decide(self, context: AutopilotContext, *, max_actions: int = 5) -> AutopilotDecision:
        actions = sorted(
            [action for action in context.candidate_actions if action.can_delegate],
            key=lambda action: (_priority_rank(action.priority), action.title),
        )[: max(1, max_actions)]
        status = _decision_status(context, actions)
        summary = (
            f"Autopilot Brain {status}: {len(actions)} acao(oes) delegavel(is), "
            f"{len(context.blockers)} bloqueio(s), score {context.score}/100."
        )
        return AutopilotDecision(
            project_id=context.project_id,
            mode=context.mode,
            status=status,
            summary=summary,
            score=context.score,
            actions=actions,
            blockers=list(context.blockers),
            signals=list(context.signals),
            generated_at=utc_now(),
        )

    async def decide_from_provider(
        self,
        provider: AutopilotContextProvider,
        project_id: str,
        *,
        mode: AutopilotMode = "assisted",
        horizon_days: int = 7,
        max_actions: int = 5,
    ) -> AutopilotDecision:
        context = await provider.build_context(
            project_id,
            mode=mode,
            horizon_days=horizon_days,
            max_actions=max_actions,
        )
        return self.decide(context, max_actions=max_actions)
