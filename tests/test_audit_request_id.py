import json
import uuid

from app.db import get_session
from app.models import AuditLog, OutboxEvent
from app.worker import run_once


def _get_json(obj, *attrs) -> dict:
    """
    Prende il primo attributo esistente tra attrs e lo interpreta come JSON.
    Supporta: str, bytes/bytearray, dict. Se trova SQLAlchemy MetaData lo ignora.
    """
    for attr in attrs:
        if not hasattr(obj, attr):
            continue
        val = getattr(obj, attr)

        # SQLAlchemy Base.metadata / MetaData() -> NON è JSON applicativo
        if val.__class__.__name__ == "MetaData":
            continue

        if val is None:
            return {}

        if isinstance(val, dict):
            return val

        if isinstance(val, (bytes, bytearray)):
            val = val.decode("utf-8", errors="replace")

        if isinstance(val, str):
            return json.loads(val or "{}")

        # fallback: non sappiamo cos'è
        raise TypeError(f"{obj.__class__.__name__}.{attr} is {type(val)} not JSON-compatible")

    raise AssertionError(
        f"{obj.__class__.__name__} has none of attrs {attrs}. "
        f"Available attrs: {sorted([a for a in dir(obj) if not a.startswith('_')])}"
    )


def _get_meta_json_str(obj) -> str:
    # Supporta naming diversi nel modello (meta_json, metadata, ecc.)
    for attr in (
        "meta_json",
        "metadata",          # <-- QUESTO
        "meta",
        "meta_text",
        "meta_json_text",
        "meta_data",
        "metadata_json",
    ):
        if hasattr(obj, attr):
            val = getattr(obj, attr)
            return val or "{}"
    raise AssertionError(
        f"{obj.__class__.__name__} has no known meta field. "
        f"Available attrs: {sorted([a for a in dir(obj) if not a.startswith('_')])}"
    )


def test_request_id_propagated_to_audit_meta(client):
    # procurement crea supplier
    login = client.post("/auth/login", json={"username": "procurement", "password": "procurement"})
    assert login.status_code == 200
    p_token = login.json()["access_token"]

    # quality crea NC (se RBAC lo permette) altrimenti usa procurement anche qui
    login2 = client.post("/auth/login", json={"username": "quality", "password": "quality"})
    assert login2.status_code == 200
    q_token = login2.json()["access_token"]

    # 1) Create supplier
    supplier_name = f"RID_SUP_{uuid.uuid4().hex}"
    resp_sup = client.post(
        "/suppliers",
        json={"name": supplier_name},
        headers={"Authorization": f"Bearer {p_token}"},
    )
    assert resp_sup.status_code in (200, 201)
    supplier_id = resp_sup.json()["id"]

    # Snapshot: audit id massimo PRIMA del worker (così filtriamo solo "nuovi audit")
    with get_session() as s:
        last_audit_id = s.query(AuditLog.id).order_by(AuditLog.id.desc()).first()
        last_audit_id = last_audit_id[0] if last_audit_id else 0

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

    # Assert API -> Outbox: request_id deve essere nel meta_json dell'evento PENDING
    with get_session() as s:
        pending = s.query(OutboxEvent).filter(OutboxEvent.status == "PENDING").all()
        assert len(pending) == 1
        outbox = pending[0]
        outbox_payload = _get_json(outbox, "payload_json")
        assert outbox_payload.get("request_id") == "test-rid-123", (
            "OutboxEvent.payload_json must contain request_id from X-Request-ID header"
        )

    # 3) Run worker once to handle outbox -> writes audit
    n = run_once()
    assert n >= 1

    # 4) Assert Outbox -> Worker -> Audit: request_id deve comparire nei nuovi audit
    with get_session() as s:
        new_rows = (
            s.query(AuditLog)
            .filter(AuditLog.id > last_audit_id)
            .order_by(AuditLog.id.desc())
            .limit(50)
            .all()
        )

    assert new_rows, "Expected at least one new audit row after worker run"
    assert any(
        _get_json(r, "meta_json").get("request_id") == "test-rid-123"
        for r in new_rows
    ), "No new audit row found with meta_json.request_id == 'test-rid-123'"
