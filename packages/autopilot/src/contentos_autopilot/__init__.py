"""Strategic Autopilot brain for ContentOS.

This package only produces decisions and read models. Execution remains in
Growth, Workflow Engine, Scheduler, Publisher, Analytics, Memory and Learning.
"""

from contentos_autopilot.brain import AutopilotBrain
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
from contentos_autopilot.objectives import (
    ObjectiveNode,
    ObjectiveTree,
    build_objective_tree,
    objective_metadata_for_topic,
)
from contentos_autopilot.twin import ChannelTwinSnapshot, build_channel_twin_snapshot

__all__ = [
    "AutopilotAction",
    "AutopilotBrain",
    "AutopilotContext",
    "AutopilotDecision",
    "AutopilotMode",
    "AutopilotSignal",
    "ChannelTwinSnapshot",
    "MarketIntelligenceReport",
    "MarketSignal",
    "ObjectiveNode",
    "ObjectiveTree",
    "SaturationSignal",
    "TrendOpportunity",
    "build_objective_tree",
    "build_market_intelligence_report",
    "build_channel_twin_snapshot",
    "objective_metadata_for_topic",
]
