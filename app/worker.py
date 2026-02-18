from __future__ import annotations

import time
import logging
import uuid

from datetime import datetime, timezone, timedelta
from typing import List

from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import OutboxEvent, ProcessedEvent
from app.events.handlers import handle_nc_created, handle_nc_closed, handle_supplier_cert_updated
from app.settings import get_settings
from app.logging_utils import configure_logging, set_request_id


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
    SQLite: best-effort claim (tests assume single worker, but reclaim logic still works).

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
        # Claim it (or reclaim it)
        ev.status = "PROCESSING"
        ev.locked_by = worker_id
        ev.locked_at = now
        ev.attempts += 1
        claimed_ids.append(ev.id)

    session.flush()
    return claimed_ids


def run_once(limit: int | None = None) -> int:
    settings = get_settings()
    batch = limit if limit is not None else settings.OUTBOX_BATCH_SIZE

    processed = 0
    worker_id = "worker"  # demo: stable id; could be hostname/pid later

    batch_rid = f"worker:{uuid.uuid4()}"
    set_request_id(batch_rid)

    # 1) Atomically claim candidate IDs in a single transaction.
    with get_session() as session:
        event_ids = claim_outbox_ids(
            session,
            limit=batch,
            worker_id=worker_id,
            lock_timeout_sec=settings.OUTBOX_LOCK_TIMEOUT_SEC,
        )

    # 2) Process each claimed event in its own transaction/session (1-event-1-transaction semantics).
    for outbox_id in event_ids:
        with get_session() as session:
            ev = session.get(OutboxEvent, outbox_id)
            if ev is None:
                continue

            # If status changed unexpectedly, skip.
            if ev.status != "PROCESSING":
                continue

            try:
                process_one_event(session, ev)
                processed += 1
            except Exception as e:
                # Release lock; either requeue or fail permanently.
                if ev.attempts >= settings.OUTBOX_MAX_ATTEMPTS:
                    ev.status = "FAILED"
                else:
                    ev.status = "PENDING"

                ev.locked_by = None
                ev.locked_at = None
                session.flush()
                print(f"[worker] error processing event id={ev.id} type={ev.event_type}: {e}")

    set_request_id(None)

    return processed


def main() -> None:
    print("[worker] starting (polling mode). CTRL+C to stop.")

    settings = get_settings()
    configure_logging(level=settings.LOG_LEVEL, json_logs=settings.LOG_JSON)
    logger = logging.getLogger("qhse.worker")
    logger.info("worker starting", extra={"status": "starting"})

    while True:
        n = run_once()
        if n:
            print(f"[worker] processed {n} event(s)")
        time.sleep(1.0)


if __name__ == "__main__":
    main()
