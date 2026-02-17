from __future__ import annotations

import worker

from app.db import get_session
from app.models import AuditLog, OutboxEvent, ProcessedEvent
from tests.utils_auth import auth_headers, login_and_get_token


def test_worker_is_idempotent_on_rerun(client):
    # Auth headers
    token_p = login_and_get_token(client, "procurement", "procurement")
    headers_p = auth_headers(token_p)

    token_q = login_and_get_token(client, "quality", "quality")
    headers_q = auth_headers(token_q)

    # 1) create supplier (write -> procurement/admin)
    r1 = client.post(
        "/suppliers",
        json={"name": "ACME", "certification_expiry": None},
        headers=headers_p,
    )
    assert r1.status_code in (200, 201), r1.text
    supplier_id = r1.json()["id"]

    # 2) create NC (write -> quality/admin) -> should create outbox event
    r2 = client.post(
        "/ncs",
        json={"supplier_id": supplier_id, "severity": "low", "description": "x"},
        headers=headers_q,
    )
    assert r2.status_code == 201, r2.text

    # Capture stable event UUID used for dedup
    with get_session() as s:
        pending = s.query(OutboxEvent).filter(OutboxEvent.status == "PENDING").all()
        assert len(pending) == 1
        outbox_event_id = pending[0].event_id

    # 3) first run processes the event
    processed_1 = worker.run_once()
    assert processed_1 == 1

    with get_session() as s:
        audit_1 = s.query(AuditLog).count()
        pe_1 = (
            s.query(ProcessedEvent)
            .filter(ProcessedEvent.event_id == outbox_event_id)
            .count()
        )
        assert pe_1 == 1
        assert audit_1 == 1

    # 4) second run must do nothing (idempotent)
    processed_2 = worker.run_once()
    assert processed_2 == 0

    with get_session() as s:
        audit_2 = s.query(AuditLog).count()
        pe_2 = (
            s.query(ProcessedEvent)
            .filter(ProcessedEvent.event_id == outbox_event_id)
            .count()
        )
        assert pe_2 == 1
        assert audit_2 == 1
