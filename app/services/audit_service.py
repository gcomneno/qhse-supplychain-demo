from __future__ import annotations

from sqlalchemy import select

from app.models import AuditLog


def list_audit_logs(session, offset: int = 0, limit: int = 20) -> list[AuditLog]:
    q = (
        select(AuditLog)
        .order_by(AuditLog.id.desc())  # latest first
        .offset(offset)
        .limit(limit)
    )
    return list(session.execute(q).scalars().all())
