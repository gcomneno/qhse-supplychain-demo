from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import require_role
from app.db import get_session
from app.schemas import AuditLogOut
from app.services.audit_service import list_audit_logs

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get(
    "",
    response_model=list[AuditLogOut],
    dependencies=[Depends(require_role(["auditor", "admin"]))],
)
def get_audit_log(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    with get_session() as session:
        return list_audit_logs(session, offset=offset, limit=limit)
