from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db import get_session
from app.schemas import SupplierCreate, SupplierOut, SupplierDetailOut, SupplierCertUpdate
from app.services.supplier_service import create_supplier, get_supplier_detail, update_supplier_certification


router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.post("", response_model=SupplierOut, status_code=201)
def post_supplier(payload: SupplierCreate):
    try:
        with get_session() as session:
            s = create_supplier(session, payload.name, payload.certification_expiry)
            return s
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{supplier_id}", response_model=SupplierDetailOut)
def get_supplier(supplier_id: int):
    try:
        with get_session() as session:
            return get_supplier_detail(session, supplier_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{supplier_id}/certification", response_model=SupplierOut)
def patch_supplier_cert(supplier_id: int, payload: SupplierCertUpdate):
    try:
        with get_session() as session:
            s = update_supplier_certification(session, supplier_id, payload.certification_expiry)
            return s
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
