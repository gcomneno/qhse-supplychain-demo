import json
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_session
from app.models import AuditLog
from app.worker import run_once


def test_request_id_propagated_to_audit_meta():
    client = TestClient(app)

    # procurement crea supplier
    login = client.post("/auth/login", json={"username": "procurement", "password": "procurement"})
    assert login.status_code == 200
    p_token = login.json()["access_token"]

    # quality crea NC (se RBAC lo permette) altrimenti usa procurement anche qui
    login2 = client.post("/auth/login", json={"username": "quality", "password": "quality"})
    assert login2.status_code == 200
    q_token = login2.json()["access_token"]

    # 1) Create supplier (no audit expected here)
    supplier_name = f"RID_SUP_{uuid.uuid4().hex}"
    resp_sup = client.post(
        "/suppliers",
        json={"name": supplier_name},
        headers={"Authorization": f"Bearer {p_token}"},
    )
    assert resp_sup.status_code in (200, 201)
    supplier_id = resp_sup.json()["id"]

    # 2) Create NC with request id header (this enqueues outbox event)
    headers = {
        "Authorization": f"Bearer {q_token}",
        "X-Request-ID": "test-rid-123",
    }
    resp_nc = client.post(
        "/ncs",
        json={"supplier_id": supplier_id, "severity": "low", "description": "rid test"},
        headers=headers,
    )
    assert resp_nc.status_code in (200, 201)

    # 3) Run worker once to handle outbox -> writes audit
    n = run_once()
    assert n >= 1

    # 4) Assert audit contains request_id
    with get_session() as s:
        rows = (
            s.query(AuditLog)
            .filter(AuditLog.action == "NC_CREATED_HANDLED")
            .order_by(AuditLog.id.desc())
            .limit(20)
            .all()
        )

    assert rows, "Expected at least one NC_CREATED_HANDLED audit row"
    assert any(
        json.loads(r.meta_json or "{}").get("request_id") == "test-rid-123"
        for r in rows
    ), "No NC_CREATED_HANDLED audit row found with meta_json.request_id == 'test-rid-123'"
