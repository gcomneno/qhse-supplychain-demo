# tests/test_worker_failure_policy.py
from __future__ import annotations

import uuid

import app.worker as worker

from app.db import get_session
from app.models import OutboxEvent, ProcessedEvent


def test_worker_retries_unknown_event_and_does_not_mark_processed(client):
    # Arrange: insert a poison event directly in outbox
    event_uuid = str(uuid.uuid4())
    with get_session() as s:
        ev = OutboxEvent(
            event_id=event_uuid,
            event_type="SOMETHING_UNKNOWN",
            payload_json="{}",
            status="PENDING",
            attempts=0,
        )
        s.add(ev)
        s.flush()
        outbox_row_id = ev.id

    # Act: first run -> should fail, keep it pending, attempts=1
    processed = worker.run_once()

    # Assert
    assert processed == 0

    with get_session() as s:
        ev2 = s.get(OutboxEvent, outbox_row_id)
        assert ev2 is not None
        assert ev2.status == "PENDING"
        assert ev2.attempts == 1

        # Must NOT mark as processed if it failed
        assert s.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_uuid).count() == 0


def test_worker_marks_unknown_event_failed_after_5_attempts(client):
    # Arrange
    event_uuid = str(uuid.uuid4())
    with get_session() as s:
        ev = OutboxEvent(
            event_id=event_uuid,
            event_type="SOMETHING_UNKNOWN",
            payload_json="{}",
            status="PENDING",
            attempts=0,
        )
        s.add(ev)
        s.flush()
        outbox_row_id = ev.id

    # Act: run 5 times -> attempts reaches 5 -> status FAILED
    for _ in range(5):
        processed = worker.run_once()
        assert processed == 0  # unknown event never succeeds

    # Assert
    with get_session() as s:
        ev2 = s.get(OutboxEvent, outbox_row_id)
        assert ev2 is not None
        assert ev2.attempts == 5
        assert ev2.status == "FAILED"
        assert s.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_uuid).count() == 0
