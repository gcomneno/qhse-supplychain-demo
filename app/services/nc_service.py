from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NonConformity, Supplier
from app.events.outbox import enqueue_event


def create_nc(session: Session, supplier_id: int, severity: str, description: str) -> NonConformity:
    supplier = session.get(Supplier, supplier_id)
    if supplier is None:
        raise ValueError("Supplier not found")

    nc = NonConformity(
        supplier_id=supplier_id,
        severity=severity,
        status="OPEN",
        description=description,
    )
    session.add(nc)
    session.flush()  # assigns nc.id

    # OUTBOX event written in the SAME transaction
    enqueue_event(
        session,
        event_type="NC_CREATED",
        payload={
            "nc_id": nc.id,
            "supplier_id": supplier_id,
            "severity": severity,
        },
    )

    return nc


def close_nc(session: Session, nc_id: int) -> NonConformity:
    nc = session.get(NonConformity, nc_id)
    if nc is None:
        raise ValueError("NC not found")
    nc.status = "CLOSED"
    session.flush()

    # evento outbox per mostrare che anche la chiusura è event-driven
    enqueue_event(
        session,
        event_type="NC_CLOSED",
        payload={"nc_id": nc.id},
    )
    return nc


def list_ncs(session, offset: int = 0, limit: int = 20) -> list[NonConformity]:
    q = (
        select(NonConformity)
        .order_by(NonConformity.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.execute(q).scalars().all())
