from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_suppliers import router as suppliers_router
from app.api.routes_ncs import router as ncs_router
from app.api.routes_kpi import router as kpi_router
from app.api.routes_auth import router as auth_router
from app.api.routes_audit_log import router as audit_log_router


app = FastAPI(title="QHSE Supply Chain - Demo")


app.include_router(suppliers_router)
app.include_router(kpi_router)
app.include_router(ncs_router)
app.include_router(auth_router)
app.include_router(audit_log_router)


@app.get("/health")
def health():
    return {"status": "ok"}
