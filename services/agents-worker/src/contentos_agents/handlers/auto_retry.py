"""Auto Retry step — creative + retention retry checkpoint (V5.2.2)."""

from __future__ import annotations

import json
import os

from contentos_intelligence.application.retention.retry_policy import plan_retention_retry, retention_retry_enabled
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.audiovisual_qa import evaluate_publish_gate
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta


def _max_creative_retries() -> int:
    try:
        return max(0, int(os.getenv("MAX_CREATIVE_RETRIES", "1")))
    except ValueError:
        return 1


def _retry_from(payload: dict) -> str:
    retention_plan = coerce_dict(payload.get("retention_retry_plan"))
    if retention_retry_enabled() and retention_plan and not retention_plan.get("passed", True):
        step = str(retention_plan.get("retry_from") or "").strip()
        if step:
            return step
    configured = str(payload.get("creative_retry_from") or "").strip()
    if configured:
        return configured
    return os.getenv("CREATIVE_RETRY_FROM", "script").strip() or "script"


def _combined_passed(payload: dict, review: dict) -> bool:
    video_passed = bool(payload.get("video_review_passed", review.get("passed", True)))
    if "retention_passed" in payload and retention_retry_enabled():
        return video_passed and bool(payload.get("retention_passed"))
    return video_passed


class AutoRetryAgentHandler(BaseAgentHandler):
    step = "auto_retry"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        payload = dict(task_input.payload)
        review = coerce_dict(payload.get("video_review"))
        retention_report = coerce_dict(payload.get("retention_report"))
        retention_plan = plan_retention_retry(
            retention_report if retention_retry_enabled() and retention_report else None
        )
        passed = _combined_passed(payload, review)
        publish_gate = evaluate_publish_gate(payload)
        score = payload.get("video_score", review.get("score"))
        retention_score = payload.get("retention_score", retention_plan.retention_score)
        min_score = review.get("min_score")
        retry_from = _retry_from(payload)
        max_retries = _max_creative_retries()

        decision = "advance" if passed else "engine_decides"
        logs = [
            f"[auto_retry] Review passed={passed} video_score={score} min={min_score}",
            f"Retention passed={payload.get('retention_passed', 'n/a')} score={retention_score}",
            f"Retry policy: max={max_retries} from='{retry_from}'",
        ]
        if retention_plan.target:
            logs.append(f"Retention target={retention_plan.target} reason={retention_plan.reason}")
        if passed:
            logs.append("No retry needed; advancing pipeline")
        else:
            logs.append("Below threshold; workflow engine will retry or continue if budget is exhausted")

        report = {
            "passed": passed,
            "publishable": publish_gate["publishable"],
            "publish_block_reasons": publish_gate["block_reasons"],
            "video_score": score,
            "retention_score": retention_score,
            "min_score": min_score,
            "retry_from": retry_from,
            "retention_retry_target": retention_plan.target,
            "retention_retry_reason": retention_plan.reason,
            "max_retries": max_retries,
            "decision": decision,
        }
        ref = await self.get_asset_manager().store(
            AssetCategory.ASSETS,
            json.dumps(report, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="auto_retry.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "auto_retry": report,
                "auto_retry_decision": decision,
                "publishable": publish_gate["publishable"],
                "publish_block_reasons": publish_gate["block_reasons"],
                "audiovisual_qa_gate": publish_gate,
                "video_review_passed": bool(payload.get("video_review_passed", review.get("passed", True))),
                "retention_passed": bool(payload.get("retention_passed", retention_plan.passed)),
                "video_score": score,
                "retention_score": retention_score,
                "video_review": review,
                "retention_retry_plan": retention_plan.to_dict(),
                "creative_retry_from": retry_from,
            },
            logs=logs,
        )
