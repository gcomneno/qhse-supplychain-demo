from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db import get_session
from app.schemas import NCCreate, NCOut
from app.services.nc_service import create_nc, close_nc
from fastapi import Depends
from app.auth import require_role


router = APIRouter(prefix="/ncs", tags=["ncs"])


@router.post("", response_model=NCOut, status_code=201)
def post_nc(payload: NCCreate):
    try:
        with get_session() as session:
            nc = create_nc(session, payload.supplier_id, payload.severity, payload.description)
            return nc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{nc_id}/close", response_model=NCOut)
def patch_close_nc(nc_id: int):
    try:
        with get_session() as session:
            return close_nc(session, nc_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/suppliers", dependencies=[Depends(require_role(["procurement","admin"]))])
def create_supplier(...):
    ...


@router.get("/suppliers", dependencies=[Depends(require_role(["auditor","quality","procurement","admin"]))])
def list_suppliers(...):
    ...
