from opentelemetry import trace
from opentelemetry.trace import get_current_span
from contextvars import ContextVar

from app.observability.request_context import request_id_var


def get_trace_context():
    span = get_current_span()
    if not span:
        return None, None

    ctx = span.get_span_context()
    if not ctx:
        return None, None

    trace_id = format(ctx.trace_id, "032x")
    span_id = format(ctx.span_id, "016x")

    return trace_id, span_id


def enrich_log_record(record: dict) -> dict:
    trace_id, span_id = get_trace_context()

    record["trace_id"] = trace_id
    record["span_id"] = span_id
    record["request_id"] = request_id_var.get(None)

    return record
