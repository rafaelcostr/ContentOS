"""Performance Learning — V5.4.2."""

from contentos_intelligence.application.performance_learning.pipeline_feedback import (
    build_pipeline_performance_feedback,
)
from contentos_intelligence.application.performance_learning.scoring import compute_ctr, min_ctr, min_views
from contentos_intelligence.application.performance_learning.service import (
    auto_apply_memory,
    auto_index_kb,
    list_performance_insights,
    performance_learning_enabled,
    process_project_performance_learning,
)

__all__ = [
    "auto_apply_memory",
    "auto_index_kb",
    "build_pipeline_performance_feedback",
    "compute_ctr",
    "list_performance_insights",
    "min_ctr",
    "min_views",
    "performance_learning_enabled",
    "process_project_performance_learning",
]
