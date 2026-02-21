from __future__ import annotations

import logging
import time
import uuid
import json

from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.events.handlers import (
    handle_nc_closed,
    handle_nc_created,
    handle_supplier_cert_updated,
)
from app.logging_utils import configure_logging, set_request_id, get_request_id
from app.models import OutboxEvent, ProcessedEvent
from app.settings import get_settings
from app.observability.worker_tracing import setup_worker_tracing

from opentelemetry.propagate import extract
from opentelemetry import trace

from prometheus_client import Counter, Histogram, Gauge


# --- Worker RED metrics ---
worker_poll_iterations_total = Counter(
    "worker_poll_iterations_total",
    "Total polling iterations",
    ["result"],  # ok | empty | error
)

worker_poll_duration_seconds = Histogram(
    "worker_poll_duration_seconds",
    "Duration of worker polling iteration",
)

worker_jobs_processed_total = Counter(
    "worker_jobs_processed_total",
    "Total processed jobs",
    ["status", "event_type"],  # success|failed ; event_type low-card
)

worker_job_duration_seconds = Histogram(
    "worker_job_duration_seconds",
    "Duration of single job processing",
    ["event_type"],
)

# --- Outbox health metrics ---
outbox_unprocessed_total = Gauge(
    "outbox_unprocessed_total",
    "Number of unprocessed outbox events (PENDING+PROCESSING)",
)

outbox_oldest_unprocessed_age_seconds = Gauge(
    "outbox_oldest_unprocessed_age_seconds",
    "Age of oldest unprocessed outbox event in seconds",
)


logger = logging.getLogger("qhse.worker")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_already_processed(session: Session, event_id: str) -> bool:
    q = select(ProcessedEvent).where(ProcessedEvent.event_id == event_id)
    return session.execute(q).scalar_one_or_none() is not None


def mark_processed(session: Session, event_id: str) -> None:
    session.add(ProcessedEvent(event_id=event_id))


def process_one_event(session: Session, ev: OutboxEvent) -> None:
    # Idempotenza: se già processato, non rifare effetti
    if is_already_processed(session, ev.event_id):
        ev.status = "DONE"
        ev.processed_at = utcnow()
        ev.locked_by = None
        ev.locked_at = None
        return

    if ev.event_type == "NC_CREATED":
        handle_nc_created(session, ev.payload_json)
    elif ev.event_type == "NC_CLOSED":
        handle_nc_closed(session, ev.payload_json)
    elif ev.event_type == "SUPPLIER_CERT_UPDATED":
        handle_supplier_cert_updated(session, ev.payload_json)
    else:
        raise ValueError(f"Unknown event_type: {ev.event_type}")

    mark_processed(session, ev.event_id)
    ev.status = "DONE"
    ev.processed_at = utcnow()
    ev.locked_by = None
    ev.locked_at = None


def claim_outbox_ids(
    session: Session,
    *,
    limit: int,
    worker_id: str,
    lock_timeout_sec: int,
) -> List[int]:
    """
    Atomically claim a batch of outbox events.

    Postgres: uses SELECT ... FOR UPDATE SKIP LOCKED (true multi-worker safety).
    Reclaim rule: PROCESSING events with locked_at older than now - lock_timeout_sec are reclaimable.
    """
    now = utcnow()
    stale_cutoff = now - timedelta(seconds=lock_timeout_sec)

    reclaimable_processing = and_(
        OutboxEvent.status == "PROCESSING",
        or_(OutboxEvent.locked_at.is_(None), OutboxEvent.locked_at < stale_cutoff),
    )

    claim_filter = or_(
        OutboxEvent.status == "PENDING",
        reclaimable_processing,
    )

    dialect = session.get_bind().dialect.name

    q = (
        select(OutboxEvent)
        .where(claim_filter)
        .order_by(OutboxEvent.id.asc())
        .limit(limit)
    )

    if dialect == "postgresql":
        q = q.with_for_update(skip_locked=True)

    # IMPORTANT: keep this claim inside the current transaction.
    rows = list(session.execute(q).scalars())

    claimed_ids: List[int] = []
    for ev in rows:
        ev.status = "PROCESSING"
        ev.locked_by = worker_id
        ev.locked_at = now
        ev.attempts += 1
        claimed_ids.append(ev.id)

    session.flush()
    return claimed_ids


def _claim_batch(batch: int, worker_id: str, settings) -> list[int]:
    with get_session() as session:
        return claim_outbox_ids(
            session,
            limit=batch,
            worker_id=worker_id,
            lock_timeout_sec=settings.OUTBOX_LOCK_TIMEOUT_SEC,
        )


def _start_worker_span(tp: str | None):
    tracer = trace.get_tracer("qhse.worker")

    if tp:
        ctx = extract({"traceparent": tp})
        return tracer.start_as_current_span("worker.process_event", context=ctx)

    return tracer.start_as_current_span("worker.process_event")


def _process_single_event(session, ev: OutboxEvent, settings) -> int:
    t1 = time.time()
    try:
        prev_rid = get_request_id()
        rid, tp = _parse_meta(ev.meta_json)

        if rid:
            set_request_id(rid)

        with _start_worker_span(tp):
            process_one_event(session, ev)

        worker_jobs_processed_total.labels(status="success", event_type=ev.event_type).inc()
        return 1
    except Exception:
        worker_jobs_processed_total.labels(status="failed", event_type=ev.event_type).inc()
        _handle_processing_error(session, ev, settings)
        return 0
    finally:
        worker_job_duration_seconds.labels(event_type=ev.event_type).observe(time.time() - t1)
        set_request_id(prev_rid)
        return 1


def _parse_meta(meta_json: str | None) -> tuple[str | None, str | None]:
    if not meta_json:
        return None, None

    try:
        meta = json.loads(meta_json) or {}
        if not isinstance(meta, dict):
            return None, None
    except Exception:
        logger.warning("invalid meta_json; ignoring")
        return None, None

    rid = meta.get("request_id")
    tp = meta.get("traceparent") or meta.get("trace_parent")
    return rid, tp


def _handle_processing_error(session, ev: OutboxEvent, settings) -> None:
    if ev.attempts >= settings.OUTBOX_MAX_ATTEMPTS:
        ev.status = "FAILED"
    else:
        ev.status = "PENDING"

    ev.locked_by = None
    ev.locked_at = None
    session.flush()

    logger.exception(
        "error processing event",
        extra={
            "outbox_id": ev.id,
            "event_type": ev.event_type,
            "status": ev.status,
            "attempts": ev.attempts,
        },
    )


def run_once(limit: int | None = None) -> int:
    t0 = time.time()

    settings = get_settings()
    batch = limit if limit is not None else settings.OUTBOX_BATCH_SIZE

    processed = 0
    worker_id = "worker"

    batch_rid = f"worker:{uuid.uuid4()}"
    set_request_id(batch_rid)

    try:
        event_ids = _claim_batch(batch, worker_id, settings)

        for outbox_id in event_ids:
            with get_session() as session:
                ev = session.get(OutboxEvent, outbox_id)
                if not ev or ev.status != "PROCESSING":
                    continue

                processed += _process_single_event(session, ev, settings)

        if processed == 0:
            worker_poll_iterations_total.labels(result="empty").inc()
        else:
            worker_poll_iterations_total.labels(result="ok").inc()

        # Outbox health (one query per loop)
        with get_session() as session:
            q = session.query(OutboxEvent).filter(OutboxEvent.status.in_(["PENDING", "PROCESSING"]))
            outbox_unprocessed_total.set(q.count())

            oldest = q.order_by(OutboxEvent.created_at.asc()).first()
            if oldest and oldest.created_at:
                age = (datetime.utcnow() - oldest.created_at).total_seconds()
                outbox_oldest_unprocessed_age_seconds.set(age)
            else:
                outbox_oldest_unprocessed_age_seconds.set(0)

        return processed

    finally:
        worker_poll_duration_seconds.observe(time.time() - t0)
        set_request_id(None)


def main() -> None:
    settings = get_settings()

    # 1) logging prima (perché configure_logging() resetta gli handler)
    configure_logging(level=settings.LOG_LEVEL, json_logs=settings.LOG_JSON)

    # 2) tracing dopo
    setup_worker_tracing(enabled=settings.ENABLE_TRACING)

    # 3) metrics endpoint (Prometheus pull)
    #    Nota: start_http_server avvia un server HTTP in background (thread daemon).
    from os import getenv
    from prometheus_client import start_http_server

    metrics_port = int(getenv("WORKER_METRICS_PORT", "9100"))
    start_http_server(metrics_port)
    logger.info("worker metrics server started", extra={"port": metrics_port})

    logger.info("worker starting", extra={"status": "starting"})

    from opentelemetry import trace
    tracer = trace.get_tracer("qhse.worker")

    while True:
        with tracer.start_as_current_span("worker.loop"):
            try:
                n = run_once()
            except Exception:
                worker_poll_iterations_total.labels(result="error").inc()
                raise
            else:
                if n:
                    logger.info("batch processed", extra={"status": "processed", "count": n})
        time.sleep(1.0)


if __name__ == "__main__":
    main()
