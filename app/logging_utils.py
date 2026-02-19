from __future__ import annotations

import json
import logging
import sys

from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from opentelemetry.trace import get_current_span


_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(rid: str | None) -> None:
    _request_id.set(rid)


def get_request_id() -> str | None:
    return _request_id.get()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Trace context enrichment
        span = get_current_span()
        if span:
            ctx = span.get_span_context()
            if ctx and ctx.trace_id != 0:
                payload["trace_id"] = format(ctx.trace_id, "032x")
                payload["span_id"] = format(ctx.span_id, "016x")

        rid = getattr(record, "request_id", None)
        if rid:
            payload["request_id"] = rid

        # Common extras (safe if missing)
        for key in ("event_type", "outbox_id", "event_id", "status", "attempts"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(*, level: str = "INFO", json_logs: bool = True) -> None:
    """
    Configure root logging once, stdlib-only.
    """
    root = logging.getLogger()
    if getattr(root, "_qhse_configured", False):
        return

    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setLevel(level.upper())

    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    # Drop any pre-existing handlers to avoid double logs under reload
    root.handlers.clear()
    root.addHandler(handler)

    # Tame uvicorn loggers (still go through root handler)
    logging.getLogger("uvicorn").setLevel(level.upper())
    logging.getLogger("uvicorn.error").setLevel(level.upper())
    logging.getLogger("uvicorn.access").setLevel(level.upper())

    root._qhse_configured = True  # type: ignore[attr-defined]
