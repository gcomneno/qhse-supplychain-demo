from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import OutboxEvent, ProcessedEvent
from app.events.handlers import handle_nc_created, handle_nc_closed, handle_supplier_cert_updated


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


def run_once(limit: int = 10) -> int:
    processed = 0

    # 1) Fetch candidate IDs in a short-lived session.
    #    IMPORTANT: we only carry IDs across sessions (not ORM objects),
    #    to guarantee 1-event-1-transaction semantics.
    with get_session() as session:
        q_ids = (
            select(OutboxEvent.id)
            .where(OutboxEvent.status == "PENDING")
            .order_by(OutboxEvent.id.asc())
            .limit(limit)
        )
        event_ids = list(session.execute(q_ids).scalars())

    # 2) Process each event in its own transaction/session.
    for outbox_id in event_ids:
        with get_session() as session:
            ev = session.get(OutboxEvent, outbox_id)
            if ev is None:
                continue

            # Status might have changed since we selected candidate IDs.
            if ev.status != "PENDING":
                continue

            try:
                ev.status = "PROCESSING"
                ev.attempts += 1
                session.flush()

                process_one_event(session, ev)
                processed += 1
            except Exception as e:
                if ev.attempts >= 5:
                    ev.status = "FAILED"
                else:
                    ev.status = "PENDING"
                session.flush()
                print(f"[worker] error processing event id={ev.id} type={ev.event_type}: {e}")

    return processed



def main() -> None:
    print("[worker] starting (polling mode). CTRL+C to stop.")
    while True:
        n = run_once(limit=10)
        if n:
            print(f"[worker] processed {n} event(s)")
        time.sleep(1.0)


if __name__ == "__main__":
    main()
