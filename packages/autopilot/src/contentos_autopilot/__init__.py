"""Strategic Autopilot brain for ContentOS.

This package only produces decisions and read models. Execution remains in
Growth, Workflow Engine, Scheduler, Publisher, Analytics, Memory and Learning.
"""

from contentos_autopilot.brain import AutopilotBrain
from contentos_autopilot.cost import CostDecisionScore, build_cost_decision_score
from contentos_autopilot.creative import CreativeDirectionBrief, SceneBrief, build_creative_direction_brief
from contentos_autopilot.domain import (
    AutopilotAction,
    AutopilotContext,
    AutopilotDecision,
    AutopilotMode,
    AutopilotSignal,
)
from contentos_autopilot.market import (
    MarketIntelligenceReport,
    MarketSignal,
    SaturationSignal,
    TrendOpportunity,
    build_market_intelligence_report,
)
from contentos_autopilot.media import MediaSourceMix, MediaStrategyPlan, build_media_strategy_plan
from contentos_autopilot.objectives import (
    ObjectiveNode,
    ObjectiveTree,
    build_objective_tree,
    objective_metadata_for_topic,
)
from contentos_autopilot.resources import ResourceReadiness, build_resource_readiness
from contentos_autopilot.temporal import ClosedLoopCycle, ClosedLoopCyclePolicy, build_closed_loop_cycle_policy
from contentos_autopilot.twin import ChannelTwinSnapshot, build_channel_twin_snapshot
from contentos_autopilot.visual import VisualPatternSnapshot, build_visual_pattern_snapshot

__all__ = [
    "AutopilotAction",
    "AutopilotBrain",
    "AutopilotContext",
    "AutopilotDecision",
    "AutopilotMode",
    "AutopilotSignal",
    "ChannelTwinSnapshot",
    "ClosedLoopCycle",
    "ClosedLoopCyclePolicy",
    "CostDecisionScore",
    "CreativeDirectionBrief",
    "MarketIntelligenceReport",
    "MarketSignal",
    "MediaSourceMix",
    "MediaStrategyPlan",
    "ObjectiveNode",
    "ObjectiveTree",
    "ResourceReadiness",
    "SaturationSignal",
    "SceneBrief",
    "TrendOpportunity",
    "VisualPatternSnapshot",
    "build_objective_tree",
    "build_resource_readiness",
    "build_closed_loop_cycle_policy",
    "build_market_intelligence_report",
    "build_media_strategy_plan",
    "build_channel_twin_snapshot",
    "build_cost_decision_score",
    "build_creative_direction_brief",
    "build_visual_pattern_snapshot",
    "objective_metadata_for_topic",
]



