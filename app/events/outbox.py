from __future__ import annotations

import json
import uuid
from sqlalchemy.orm import Session

from app.models import OutboxEvent


def enqueue_event(session: Session, event_type: str, payload: dict) -> OutboxEvent:
    ev = OutboxEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        payload_json=json.dumps(payload, ensure_ascii=False),
        status="PENDING",
        attempts=0,
    )
    session.add(ev)
    return ev
