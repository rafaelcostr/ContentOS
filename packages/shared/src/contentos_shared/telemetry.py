"""OpenTelemetry tracing helpers (Tier E1 / ops E3).

Gracefully no-ops when disabled or when opentelemetry packages are not installed.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

_initialized = False
_tracer = None
_propagate = None
_trace_api = None


def otel_enabled() -> bool:
    return os.getenv("OTEL_ENABLED", "false").lower() in ("1", "true", "yes")


def otel_endpoint() -> str:
    return os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317").strip()


def _load_otel() -> bool:
    global _tracer, _propagate, _trace_api
    if _tracer is not None:
        return True
    try:
        from opentelemetry import trace as trace_api
        from opentelemetry.propagate import extract, inject

        _trace_api = trace_api
        _propagate = {"inject": inject, "extract": extract}
        _tracer = trace_api.get_tracer("contentos")
        return True
    except ImportError:
        return False


def init_telemetry(service_name: str) -> bool:
    """Configure OTLP exporter and auto-instrumentation. Returns True when active."""
    global _initialized
    if _initialized or not otel_enabled():
        return False
    if not _load_otel():
        return False

    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.getenv("CONTENTOS_VERSION", "0.1.0"),
            "deployment.environment": os.getenv("APP_ENV", "development"),
        }
    )
    provider = TracerProvider(resource=resource)
    endpoint = otel_endpoint()
    insecure = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() in ("1", "true", "yes")
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=insecure)))
    _trace_api.set_tracer_provider(provider)
    _tracer = _trace_api.get_tracer("contentos")

    try:
        HTTPXClientInstrumentor().instrument()
    except Exception:
        pass

    _initialized = True
    return True


def instrument_fastapi(app: Any) -> None:
    if not otel_enabled() or not _load_otel():
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        excluded = os.getenv("OTEL_FASTAPI_EXCLUDED_URLS", "/health,/metrics")
        FastAPIInstrumentor.instrument_app(app, excluded_urls=excluded)
    except Exception:
        pass


def shutdown_telemetry() -> None:
    global _initialized, _tracer, _propagate, _trace_api
    if not _initialized or not _trace_api:
        return
    try:
        provider = _trace_api.get_tracer_provider()
        if hasattr(provider, "shutdown"):
            provider.shutdown()
    except Exception:
        pass
    _initialized = False
    _tracer = None


def inject_carrier(carrier: dict[str, str]) -> None:
    if not otel_enabled() or not _load_otel() or not _propagate:
        return
    _propagate["inject"](carrier)


def extract_context(carrier: dict[str, str] | None) -> Any:
    if not carrier or not otel_enabled() or not _load_otel() or not _propagate:
        return None
    return _propagate["extract"](carrier)


def trace_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    inject_carrier(headers)
    return headers


@contextmanager
def start_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    *,
    context: Any = None,
) -> Iterator[Any]:
    if not otel_enabled() or not _load_otel() or _tracer is None:
        yield None
        return

    span_kwargs: dict[str, Any] = {}
    if context is not None:
        span_kwargs["context"] = context

    with _tracer.start_as_current_span(name, **span_kwargs) as span:
        if span and attributes:
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(key, value)
        yield span


def celery_trace_carrier() -> dict[str, str]:
    carrier: dict[str, str] = {}
    inject_carrier(carrier)
    return carrier
