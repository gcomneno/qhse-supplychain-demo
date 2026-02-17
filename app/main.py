from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

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


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add JWT Bearer auth to OpenAPI
    schema.setdefault("components", {}).setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    # Apply security globally to all endpoints except /auth/login
    paths = schema.get("paths", {})
    for path, methods in paths.items():
        if path == "/auth/login":
            continue
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            op.setdefault("security", [{"BearerAuth": []}])
            # Optional: advertise 401/403 responses (nice for demo)
            op.setdefault("responses", {})
            op["responses"].setdefault("401", {"description": "Not authenticated"})
            op["responses"].setdefault("403", {"description": "Forbidden"})

    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi
