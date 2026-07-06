"""Tier E1 — OpenTelemetry tracing."""

from contentos_shared.telemetry import (
    celery_trace_carrier,
    inject_carrier,
    otel_enabled,
    otel_endpoint,
    start_span,
    trace_headers,
)


def test_otel_disabled_by_default(monkeypatch):
    monkeypatch.delenv("OTEL_ENABLED", raising=False)
    assert otel_enabled() is False


def test_otel_enabled_flag(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    assert otel_enabled() is True


def test_otel_endpoint_default(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert otel_endpoint() == "http://localhost:4317"


def test_trace_headers_empty_when_disabled(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")
    assert trace_headers() == {}


def test_celery_carrier_empty_when_disabled(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")
    assert celery_trace_carrier() == {}


def test_inject_carrier_noop_when_disabled(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")
    carrier: dict[str, str] = {}
    inject_carrier(carrier)
    assert carrier == {}


def test_start_span_noop_when_disabled(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")
    with start_span("test.span", {"key": "value"}) as span:
        assert span is None


def test_dispatch_agent_task_includes_carrier_when_enabled(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")
    from contentos_workflow.tasks import dispatch_agent_task

    class FakeResult:
        id = "task-123"

    sent_kwargs = {}

    def fake_send_task(name, kwargs=None, queue=None, countdown=0):
        sent_kwargs.update(kwargs or {})
        return FakeResult()

    monkeypatch.setattr("contentos_workflow.tasks.celery_app.send_task", fake_send_task)
    dispatch_agent_task(
        queue="contentos.research",
        job_id="j1",
        pipeline_id="p1",
        project_id="pr1",
        step="research",
        payload={"topic": "test"},
    )
    assert "_trace_carrier" not in sent_kwargs
