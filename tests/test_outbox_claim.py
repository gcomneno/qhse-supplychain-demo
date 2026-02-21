from datetime import datetime, timezone, timedelta

from app import db as app_db
from app.models import OutboxEvent
from app.worker import claim_outbox_ids


def _utcnow():
    return datetime.now(timezone.utc)


def test_claim_is_exclusive_sequential_postgres():
    # Arrange: 2 eventi PENDING
    with app_db.SessionLocal() as s:
        s.add_all(
            [
                OutboxEvent(event_id="e1", event_type="NC_CREATED", payload_json="{}"),
                OutboxEvent(event_id="e2", event_type="NC_CREATED", payload_json="{}"),
            ]
        )
        s.commit()

    # Act: primo worker li claim-a
    with app_db.SessionLocal() as s:
        ids1 = claim_outbox_ids(s, limit=10, worker_id="w1", lock_timeout_sec=30)
        s.commit()

    assert len(ids1) == 2

    # Act: secondo worker non deve ottenere nulla (sono già PROCESSING e non stale)
    with app_db.SessionLocal() as s:
        ids2 = claim_outbox_ids(s, limit=10, worker_id="w2", lock_timeout_sec=30)
        s.commit()

    assert ids2 == []


def test_reclaim_stale_lock_postgres():
    # Arrange: 1 evento
    with app_db.SessionLocal() as s:
        s.add(OutboxEvent(event_id="e1", event_type="NC_CREATED", payload_json="{}"))
        s.commit()

    # Claim as w1
    with app_db.SessionLocal() as s:
        ids1 = claim_outbox_ids(s, limit=10, worker_id="w1", lock_timeout_sec=30)
        s.commit()

    assert ids1 == [1]

    # Make it stale
    with app_db.SessionLocal() as s:
        ev = s.get(OutboxEvent, 1)
        assert ev is not None
        ev.locked_at = _utcnow() - timedelta(seconds=999)
        s.commit()

    # Reclaim as w2
    with app_db.SessionLocal() as s:
        ids2 = claim_outbox_ids(s, limit=10, worker_id="w2", lock_timeout_sec=30)
        s.commit()

    assert ids2 == [1]

    with app_db.SessionLocal() as s:
        ev = s.get(OutboxEvent, 1)
        assert ev is not None
        assert ev.status == "PROCESSING"
        assert ev.locked_by == "w2"