# tests/test_outbox_transaction.py
from __future__ import annotations

from app.db import get_session
from app.models import OutboxEvent


def test_outbox_not_written_when_nc_create_fails(client):
    # create supplier ok
    r1 = client.post("/suppliers", json={"name": "ACME", "certification_expiry": None})
    assert r1.status_code in (200, 201), r1.text

    # create NC with missing supplier -> must fail
    r2 = client.post("/ncs", json={"supplier_id": 999999, "severity": "low", "description": "x"})
    assert r2.status_code >= 400, r2.text

    # transactional outbox: no events should have been created
    with get_session() as s:
        assert s.query(OutboxEvent).count() == 0
