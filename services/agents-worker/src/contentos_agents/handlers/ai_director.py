"""AI Director agent — partial re-run by score (V5.2.4)."""

from __future__ import annotations

import json

from contentos_intelligence.application.director import ai_director_enabled, plan_director_decision
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta


class AiDirectorAgentHandler(BaseAgentHandler):
    step = "ai_director"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        if not ai_director_enabled():
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.COMPLETED.value,
                data={"ai_director_skipped": True},
                logs=["[ai_director] Disabled via AI_DIRECTOR_ENABLED"],
            )

        script = coerce_dict(task_input.payload.get("script"))
        topic = (
            script.get("title")
            or coerce_dict(task_input.payload.get("selected_topic")).get("title")
            or task_input.payload.get("topic", "")
        )
        director_retry_count = int(task_input.payload.get("director_retry_count") or 0)
        logs = [f"[ai_director] Reviewing pipeline scores for: {topic}"]

        decision = plan_director_decision(dict(task_input.payload))
        decision_payload = decision.to_dict()

        logs.append(
            f"Overall={decision.overall_score:.1f}/100 min={decision.min_score:.0f} "
            f"action={decision.action} target={decision.target or 'n/a'}"
        )
        if not decision.passed:
            logs.append(f"Partial re-run from '{decision.retry_from}' — {decision.reason}")
        for sig in decision.weak_signals[:3]:
            logs.append(f"  weak {sig.name}={sig.score:.0f} ({sig.source})")

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(decision_payload, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="director_decision.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "director_decision": decision_payload,
                "director_passed": decision.passed,
                "director_action": decision.action,
                "director_retry_target": decision.target,
                "director_overall_score": decision.overall_score,
                "director_retry_count": director_retry_count,
                "creative_retry_from": decision.retry_from if not decision.passed else "",
            },
            logs=logs,
        )
