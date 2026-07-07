"""Retention Engine agent — second-by-second analysis (V5.2.1)."""

from __future__ import annotations

import json

from contentos_intelligence.application.retention import RetentionAnalyzer
from contentos_intelligence.application.retention.retry_policy import plan_retention_retry, retention_retry_enabled
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta


class RetentionAgentHandler(BaseAgentHandler):
    step = "retention"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        script = coerce_dict(task_input.payload.get("script"))
        topic = (
            script.get("title")
            or coerce_dict(task_input.payload.get("selected_topic")).get("title")
            or task_input.payload.get("topic", "")
        )
        logs = [f"[retention] Analyzing second-by-second retention for: {topic}"]

        report = RetentionAnalyzer().analyze(dict(task_input.payload))
        report_payload = report.to_dict()
        retry_plan = plan_retention_retry(report_payload if retention_retry_enabled() else None)
        plan_payload = retry_plan.to_dict()

        logs.append(
            f"Score={report.overall_score:.1f}/100 hook@3s={report.hook_retention_pct:.1f}% "
            f"completion={report.completion_pct:.1f}% drops={len(report.drop_seconds)} "
            f"mode={report.analysis_mode}"
        )
        if not retry_plan.passed:
            logs.append(
                f"Retention retry target={retry_plan.target} from={retry_plan.retry_from} — {retry_plan.reason}"
            )
        for seg in report.weak_segments[:3]:
            logs.append(
                f"  weak {seg.label} {seg.start_second:.0f}-{seg.end_second:.0f}s "
                f"avg={seg.avg_retention_pct:.0f}%"
            )

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(report_payload, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="retention_report.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "retention_report": report_payload,
                "retention_score": report.overall_score,
                "retention_prediction": report.overall_score,
                "retention_hook_pct": report.hook_retention_pct,
                "retention_completion_pct": report.completion_pct,
                "retention_drop_seconds": report.drop_seconds,
                "retention_passed": retry_plan.passed,
                "retention_analysis_mode": report.analysis_mode,
                "retention_render_duration_seconds": report.render_duration_seconds,
                "retention_retry_plan": plan_payload,
                "retention_retry_target": retry_plan.target,
                "creative_retry_from": retry_plan.retry_from if not retry_plan.passed else "",
            },
            logs=logs,
        )
