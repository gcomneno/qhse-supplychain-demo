from __future__ import annotations

import os
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.settings import get_settings


SERVICE_NAME = "qhse-supplychain-demo"

_initialized = False
_provider: TracerProvider | None = None
_span_processor: BatchSpanProcessor | None = None


def init_tracing(app: Any, *, enabled: bool = True) -> None:
    """
    Idempotent init:
    - safe if called multiple times (tests, re-imports)
    - instruments FastAPI/logging at most once
    - sets TracerProvider only if not already set
    - adds resource attributes: service.name, service.version, deployment.environment
    """
    global _initialized, _provider, _span_processor

    if not enabled:
        return

    if _initialized:
        return

    settings = get_settings()

    # 1) Apply FastAPI middleware instrumentation only once
    if not getattr(app, "_otel_instrumented", False):
        FastAPIInstrumentor.instrument_app(app)
        setattr(app, "_otel_instrumented", True)

    # 2) Apply logging instrumentation only once (process-wide)
    if not getattr(LoggingInstrumentor, "_qhse_instrumented", False):
        LoggingInstrumentor().instrument(set_logging_format=True)
        setattr(LoggingInstrumentor, "_qhse_instrumented", True)

    # 3) Do not override an existing SDK tracer provider
    current_provider = trace.get_tracer_provider()
    if isinstance(current_provider, TracerProvider):
        _initialized = True
        return

    service_version = getattr(settings, "APP_VERSION", None) or os.getenv("APP_VERSION", "dev")
    deployment_env = getattr(settings, "ENV", None) or os.getenv("ENV", "dev")

    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
            "service.version": service_version,
            "deployment.environment": deployment_env,
        }
    )

    provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(settings.TRACE_SAMPLING)),
    )
    trace.set_tracer_provider(provider)

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    exporter_kind = os.getenv("OTEL_TRACES_EXPORTER", "").strip().lower()

    if exporter_kind == "otlp" and endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint)
    else:
        exporter = ConsoleSpanExporter()

    span_processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(span_processor)

    _provider = provider
    _span_processor = span_processor
    _initialized = True


def shutdown_tracing() -> None:
    """Best-effort shutdown (safe to call multiple times)."""
    global _initialized, _provider, _span_processor

    if not _initialized:
        return

    try:
        if _provider is not None:
            _provider.shutdown()
    finally:
        _initialized = False
        _provider = None
        _span_processor = None
