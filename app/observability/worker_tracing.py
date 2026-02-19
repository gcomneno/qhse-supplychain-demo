from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from app.settings import get_settings


SERVICE_NAME = "qhse-supplychain-worker"


def setup_worker_tracing(*, enabled: bool = True) -> None:
    if not enabled:
        return

    settings = get_settings()

    resource = Resource.create({"service.name": SERVICE_NAME})

    provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(settings.TRACE_SAMPLING)),
    )
    trace.set_tracer_provider(provider)

    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    LoggingInstrumentor().instrument(set_logging_format=True)
