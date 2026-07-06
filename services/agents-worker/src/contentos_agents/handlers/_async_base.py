"""V2 async agents — no workflow callback (fire-and-forget)."""

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.schemas.agent import AgentTaskOutput

try:
    from contentos_events import DomainEvent, get_event_bus
except ImportError:
    DomainEvent = None  # type: ignore[misc, assignment]

    def get_event_bus():  # type: ignore[misc]
        return None


class AsyncV2AgentHandler(BaseAgentHandler):
    """Base for analytics/thumbnail — publishes events without blocking the pipeline."""

    async def _callback(self, output: AgentTaskOutput) -> None:
        await self._on_async_complete(output)
        self._publish_event(output)

    async def _on_async_complete(self, output: AgentTaskOutput) -> None:
        """Override in subclass to persist results."""

    def _publish_event(self, output: AgentTaskOutput) -> None:
        try:
            bus = get_event_bus()
            if not bus or not DomainEvent or not hasattr(self, "_last_task_input"):
                return
            ti = self._last_task_input
            event = DomainEvent.from_agent_callback(
                step=self.step,
                project_id=ti.project_id,
                pipeline_id=ti.pipeline_id,
                job_id=output.job_id,
                status=output.status,
                payload=output.data or {},
            )
            bus.publish_sync(event)
        except Exception:
            pass
