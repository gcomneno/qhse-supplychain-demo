from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

SERVICE_NAME = "qhse-supplychain-demo"


def setup_tracing(app):
    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
        }
    )

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    console_exporter = ConsoleSpanExporter()
    span_processor = BatchSpanProcessor(console_exporter)
    provider.add_span_processor(span_processor)

    FastAPIInstrumentor.instrument_app(app)
    LoggingInstrumentor().instrument(set_logging_format=True)
