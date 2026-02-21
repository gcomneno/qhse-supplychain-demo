from __future__ import annotations

import os
from typing import Final

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.settings import get_settings


SERVICE_NAME: Final[str] = "qhse-supplychain-worker"

_initialized = False
_provider: TracerProvider | None = None


def init_worker_tracing(*, enabled: bool = True) -> None:
    """
    Idempotent worker tracing init:
    - doesn't override an existing SDK provider
    - instruments logging at most once (process-wide)
    - OTLP exporter if configured via env, otherwise Console exporter
    - adds resource attributes: service.name, service.version, deployment.environment
    """
    global _initialized, _provider

    if not enabled:
        return

    if _initialized:
        return

    # Logging instrumentation (process-wide): apply only once
    if not getattr(LoggingInstrumentor, "_qhse_instrumented", False):
        LoggingInstrumentor().instrument(set_logging_format=True)
        setattr(LoggingInstrumentor, "_qhse_instrumented", True)

    # Do not override an existing SDK tracer provider
    current_provider = trace.get_tracer_provider()
    if isinstance(current_provider, TracerProvider):
        _initialized = True
        return

    settings = get_settings()

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

    provider.add_span_processor(BatchSpanProcessor(exporter))

    _provider = provider
    _initialized = True


def shutdown_worker_tracing() -> None:
    global _initialized, _provider

    if not _initialized:
        return

    try:
        if _provider is not None:
            _provider.shutdown()
    finally:
        _initialized = False
        _provider = None


# Backward-compatible aliases
setup_worker_tracing = init_worker_tracing
shutdown = shutdown_worker_tracing
