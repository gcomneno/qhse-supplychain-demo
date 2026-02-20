from __future__ import annotations

import json
import uuid
from sqlalchemy.orm import Session

from app.logging_utils import get_request_id
from app.models import OutboxEvent


def enqueue_event(session: Session, event_type: str, payload: dict) -> OutboxEvent:
    rid = get_request_id()

    payload2 = dict(payload)
    if rid and "request_id" not in payload2:
        payload2["request_id"] = rid

    meta = {}
    if rid:
        meta["request_id"] = rid

    ev = OutboxEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        payload_json=json.dumps(payload2, ensure_ascii=False),
        meta_json=json.dumps(meta, ensure_ascii=False),
        status="PENDING",
        attempts=0,
    )
    session.add(ev)
    return ev
