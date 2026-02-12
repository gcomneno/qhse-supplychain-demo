# tests/test_worker_happy_path.py
from __future__ import annotations

import worker

from app.db import get_session
from app.models import AuditLog, OutboxEvent, ProcessedEvent


def test_worker_processes_outbox_event_and_writes_audit_and_dedup(client):
    # 1) create supplier
    r1 = client.post("/suppliers", json={"name": "ACME", "certification_expiry": None})
    assert r1.status_code in (200, 201), r1.text
    supplier_id = r1.json()["id"]

    # 2) create NC -> should create outbox event
    r2 = client.post("/ncs", json={"supplier_id": supplier_id, "severity": "low", "description": "x"})
    assert r2.status_code == 201, r2.text

    # Capture both:
    # - outbox_row_id (DB PK, int) to fetch the row
    # - outbox_event_id (stable UUID) used for idempotency/dedup
    with get_session() as s:
        pending = s.query(OutboxEvent).filter(OutboxEvent.status == "PENDING").all()
        assert len(pending) == 1
        outbox_row_id = pending[0].id
        outbox_event_id = pending[0].event_id

    # 3) run worker once
    processed_count = worker.run_once()  # should process 1
    assert processed_count == 1

    # 4) verify effects
    with get_session() as s:
        ev = s.get(OutboxEvent, outbox_row_id)
        assert ev is not None
        assert ev.status == "DONE"

        assert s.query(ProcessedEvent).filter(ProcessedEvent.event_id == outbox_event_id).count() == 1
        assert s.query(AuditLog).count() == 1
