from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_role
from app.db import get_session
from app.schemas import NCCreate, NCOut
from app.services.nc_service import close_nc, create_nc, list_ncs


router = APIRouter(prefix="/ncs", tags=["ncs"])


@router.post(
    "",
    response_model=NCOut,
    status_code=201,
    dependencies=[Depends(require_role(["quality", "admin"]))],
)
def post_nc(payload: NCCreate):
    try:
        with get_session() as session:
            nc = create_nc(
                session,
                payload.supplier_id,
                payload.severity,
                payload.description,
            )
            return nc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/{nc_id}/close",
    response_model=NCOut,
    dependencies=[Depends(require_role(["quality", "admin"]))],
)
def patch_close_nc(nc_id: int):
    try:
        with get_session() as session:
            return close_nc(session, nc_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "",
    response_model=list[NCOut],
    dependencies=[Depends(require_role(["auditor", "procurement", "quality", "admin"]))],
)
def list_ncs_endpoint(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    with get_session() as session:
        return list_ncs(session, offset=offset, limit=limit)
