from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, OutboxEvent
from app.worker import claim_outbox_ids


def _utcnow():
    return datetime.now(timezone.utc)


def test_claim_is_exclusive_sequential_sqlite():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as s:
        s.add_all(
            [
                OutboxEvent(event_id="e1", event_type="NC_CREATED", payload_json="{}"),
                OutboxEvent(event_id="e2", event_type="NC_CREATED", payload_json="{}"),
            ]
        )
        s.commit()

    with SessionLocal() as s:
        ids1 = claim_outbox_ids(s, limit=10, worker_id="w1", lock_timeout_sec=30)
        s.commit()
    assert len(ids1) == 2

    # Second claim should return nothing (already PROCESSING, not stale)
    with SessionLocal() as s:
        ids2 = claim_outbox_ids(s, limit=10, worker_id="w2", lock_timeout_sec=30)
        s.commit()
    assert ids2 == []


def test_reclaim_stale_lock_sqlite():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as s:
        ev = OutboxEvent(event_id="e1", event_type="NC_CREATED", payload_json="{}")
        s.add(ev)
        s.commit()

    # Claim as w1
    with SessionLocal() as s:
        ids1 = claim_outbox_ids(s, limit=10, worker_id="w1", lock_timeout_sec=30)
        s.commit()
    assert ids1 == [1]

    # Make it stale
    with SessionLocal() as s:
        ev = s.get(OutboxEvent, 1)
        assert ev is not None
        ev.locked_at = _utcnow() - timedelta(seconds=999)
        s.commit()

    # Reclaim as w2
    with SessionLocal() as s:
        ids2 = claim_outbox_ids(s, limit=10, worker_id="w2", lock_timeout_sec=30)
        s.commit()
    assert ids2 == [1]

    with SessionLocal() as s:
        ev = s.get(OutboxEvent, 1)
        assert ev is not None
        assert ev.status == "PROCESSING"
        assert ev.locked_by == "w2"
