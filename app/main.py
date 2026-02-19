from __future__ import annotations

import uuid

from pathlib import Path
from typing import Any, Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.api.routes_suppliers import router as suppliers_router
from app.api.routes_ncs import router as ncs_router
from app.api.routes_kpi import router as kpi_router
from app.api.routes_auth import router as auth_router
from app.api.routes_audit_log import router as audit_log_router
from app.db import get_session
from app.settings import get_settings
from app.observability.request_context import request_id_var


app = FastAPI(title="QHSE Supply Chain - Demo")

app.include_router(suppliers_router)
app.include_router(kpi_router)
app.include_router(ncs_router)
app.include_router(auth_router)
app.include_router(audit_log_router)


REQUEST_ID_HEADER = "X-Request-Id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        incoming: Optional[str] = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming.strip() if incoming and incoming.strip() else str(uuid.uuid4())

        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        try:
            response: Response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response


@app.get("/health")
def health():
    # Backward compatible legacy endpoint
    return {"status": "ok"}


@app.get("/healthz")
def healthz():
    # Liveness: process is up
    return {"status": "ok"}


def _project_root() -> Path:
    # app/main.py -> parent is app/, parent[1] is repo root
    return Path(__file__).resolve().parents[1]


def _db_ping() -> bool:
    try:
        with get_session() as s:
            s.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


def _alembic_code_head() -> str | None:
    """
    Return the migrations head revision as seen by code (migrations/).
    In docker image we expect alembic.ini + migrations/ to be present.
    """
    root = _project_root()
    alembic_ini = root / "alembic.ini"
    if not alembic_ini.exists():
        return None

    cfg = Config(str(alembic_ini))
    script = ScriptDirectory.from_config(cfg)
    return script.get_current_head()


def _alembic_db_revision() -> str | None:
    """
    Return DB revision from alembic_version.version_num.
    Returns None if table missing or query fails.
    """
    try:
        with get_session() as s:
            row = s.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
            return row[0] if row else None
    except SQLAlchemyError:
        return None


@app.get("/readyz")
def readyz():
    """
    Readiness:
    - always checks DB connectivity
    - checks migrations alignment when ENV != 'test'
      (tests use SQLite deterministic setup and may not have alembic_version)
    """
    settings = get_settings()

    details: dict[str, Any] = {
        "status": "ready",
        "checks": {
            "db": {"ok": False},
            "migrations": {"ok": True, "skipped": False},
        },
    }

    # 1) DB connectivity
    db_ok = _db_ping()
    details["checks"]["db"]["ok"] = db_ok
    if not db_ok:
        details["status"] = "not_ready"
        return JSONResponse(status_code=503, content=details)

    # 2) Migrations (skip in tests)
    if settings.ENV == "test":
        details["checks"]["migrations"]["skipped"] = True
        return details

    code_head = _alembic_code_head()
    db_rev = _alembic_db_revision()

    details["checks"]["migrations"]["code_head"] = code_head
    details["checks"]["migrations"]["db_revision"] = db_rev

    mig_ok = bool(code_head) and bool(db_rev) and (code_head == db_rev)
    details["checks"]["migrations"]["ok"] = mig_ok

    if not mig_ok:
        details["status"] = "not_ready"
        return JSONResponse(status_code=503, content=details)

    return details


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
        if path in {"/auth/login", "/health", "/healthz", "/readyz"}:
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
app.add_middleware(RequestIdMiddleware)
