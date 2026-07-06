"""Handlers that support sync pipeline jobs and async fire-and-forget dispatch."""

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.schemas.agent import AgentTaskOutput

try:
    from contentos_events import DomainEvent, get_event_bus
except ImportError:
    DomainEvent = None  # type: ignore[misc, assignment]

    def get_event_bus():  # type: ignore[misc]
        return None


class PipelineAwareHandler(BaseAgentHandler):
    """Base for V2 agents that may run as pipeline jobs or async side-tasks."""

    _async_mode: bool = False

    async def run(self, **kwargs) -> dict:
        self._async_mode = bool(kwargs.pop("async_mode", False))
        return await super().run(**kwargs)

    async def _callback(self, output: AgentTaskOutput) -> None:
        if self._async_mode:
            await self._on_async_complete(output)
            self._publish_event(output)
            return
        await super()._callback(output)

    async def _on_async_complete(self, output: AgentTaskOutput) -> None:
        """Override to chain async agents or persist results."""

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
