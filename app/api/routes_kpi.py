from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.auth import require_role
from app.db import get_session
from app.models import AuditLog, NonConformity, OutboxEvent, Supplier

router = APIRouter(prefix="/kpi", tags=["kpi"])


@router.get("", dependencies=[Depends(require_role(["auditor", "quality", "admin"]))])
def get_kpi():
    today = date.today()  # DATE, non stringa

    with get_session() as session:
        nc_open = session.execute(
            select(func.count()).select_from(NonConformity).where(NonConformity.status == "OPEN")
        ).scalar_one()

        nc_open_high = session.execute(
            select(func.count()).select_from(NonConformity).where(
                NonConformity.status == "OPEN",
                NonConformity.severity == "high",
            )
        ).scalar_one()

        nc_closed = session.execute(
            select(func.count()).select_from(NonConformity).where(NonConformity.status == "CLOSED")
        ).scalar_one()

        outbox_pending = session.execute(
            select(func.count()).select_from(OutboxEvent).where(OutboxEvent.status == "PENDING")
        ).scalar_one()

        outbox_failed = session.execute(
            select(func.count()).select_from(OutboxEvent).where(OutboxEvent.status == "FAILED")
        ).scalar_one()

        audit_events_total = session.execute(select(func.count()).select_from(AuditLog)).scalar_one()

        # Suppliers at risk = cert expired OR at least one OPEN high NC
        risk_ids_from_cert = session.execute(
            select(Supplier.id).where(
                Supplier.certification_expiry.is_not(None),
                Supplier.certification_expiry != "",
                func.to_date(Supplier.certification_expiry, "YYYY-MM-DD") < today,
            )
        ).scalars().all()

        risk_ids_from_nc = session.execute(
            select(func.distinct(NonConformity.supplier_id)).where(
                NonConformity.status == "OPEN",
                NonConformity.severity == "high",
            )
        ).scalars().all()

        suppliers_at_risk = len(set(risk_ids_from_cert).union(set(risk_ids_from_nc)))

    return {
        "nc_open": nc_open,
        "nc_open_high": nc_open_high,
        "nc_closed": nc_closed,
        "outbox_pending": outbox_pending,
        "outbox_failed": outbox_failed,
        "suppliers_at_risk": suppliers_at_risk,
        "audit_events_total": audit_events_total,
    }
