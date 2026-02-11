from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func

from app.models import Supplier
from app.models import NonConformity

from app.events.outbox import enqueue_event


def create_supplier(session: Session, name: str, certification_expiry: str | None) -> Supplier:
    s = Supplier(name=name, certification_expiry=certification_expiry)
    session.add(s)
    try:
        session.flush()  # to get s.id
    except IntegrityError:
        # unique constraint on name
        raise ValueError("Supplier name already exists")
    return s


def get_supplier_detail(session: Session, supplier_id: int) -> dict:
    s = session.get(Supplier, supplier_id)
    if s is None:
        raise ValueError("Supplier not found")

    nc_total = session.execute(
        select(func.count()).select_from(NonConformity).where(NonConformity.supplier_id == supplier_id)
    ).scalar_one()

    nc_open = session.execute(
        select(func.count()).select_from(NonConformity).where(
            NonConformity.supplier_id == supplier_id,
            NonConformity.status == "OPEN",
        )
    ).scalar_one()

    nc_open_high = session.execute(
        select(func.count()).select_from(NonConformity).where(
            NonConformity.supplier_id == supplier_id,
            NonConformity.status == "OPEN",
            NonConformity.severity == "high",
        )
    ).scalar_one()

    today = date.today().isoformat()
    cert_expired = (s.certification_expiry is not None) and (s.certification_expiry < today)

    is_at_risk = cert_expired or (nc_open_high > 0)

    return {
        "id": s.id,
        "name": s.name,
        "certification_expiry": s.certification_expiry,
        "nc_total": int(nc_total),
        "nc_open": int(nc_open),
        "nc_open_high": int(nc_open_high),
        "is_at_risk": bool(is_at_risk),
    }


def update_supplier_certification(session: Session, supplier_id: int, certification_expiry: str | None) -> Supplier:
    s = session.get(Supplier, supplier_id)
    if s is None:
        raise ValueError("Supplier not found")

    s.certification_expiry = certification_expiry
    session.flush()

    enqueue_event(
        session,
        event_type="SUPPLIER_CERT_UPDATED",
        payload={"supplier_id": s.id, "certification_expiry": s.certification_expiry},
    )
    return s
