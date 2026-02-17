from __future__ import annotations

from app.db import get_session
from app.models import AuditLog
from tests.utils_auth import auth_headers, login_and_get_token


def _seed_audit_logs(n: int = 3) -> None:
    with get_session() as s:
        for i in range(n):
            s.add(
                AuditLog(
                    actor="system",
                    action=f"action-{i}",
                    entity_type="nc",
                    entity_id=str(100 + i),
                    meta_json="{}",
                )
            )


def test_audit_log_requires_auth(client):
    r = client.get("/audit-log")
    assert r.status_code == 401, r.text


def test_audit_log_forbidden_for_quality(client):
    _seed_audit_logs(2)
    token = login_and_get_token(client, "quality", "quality")
    r = client.get("/audit-log", headers=auth_headers(token))
    assert r.status_code == 403, r.text


def test_audit_log_allowed_for_auditor_with_pagination(client):
    _seed_audit_logs(3)
    token = login_and_get_token(client, "auditor", "auditor")

    r1 = client.get("/audit-log?limit=2&offset=0", headers=auth_headers(token))
    assert r1.status_code == 200, r1.text
    data1 = r1.json()
    assert isinstance(data1, list)
    assert len(data1) == 2

    r2 = client.get("/audit-log?limit=2&offset=2", headers=auth_headers(token))
    assert r2.status_code == 200, r2.text
    data2 = r2.json()
    assert isinstance(data2, list)
    assert len(data2) == 1
