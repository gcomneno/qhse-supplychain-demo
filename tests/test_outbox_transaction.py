from __future__ import annotations

from app.db import get_session
from app.models import OutboxEvent
from tests.utils_auth import auth_headers, login_and_get_token


def test_outbox_not_written_when_nc_create_fails(client):
    # Auth headers
    token_p = login_and_get_token(client, "procurement", "procurement")
    headers_p = auth_headers(token_p)

    token_q = login_and_get_token(client, "quality", "quality")
    headers_q = auth_headers(token_q)

    # 1) create supplier ok
    r1 = client.post(
        "/suppliers",
        json={"name": "ACME", "certification_expiry": None},
        headers=headers_p,
    )
    assert r1.status_code in (200, 201), r1.text
    supplier_id = r1.json()["id"]

    # 2) create NC but force failure with invalid supplier_id
    bad_supplier_id = supplier_id + 999_999
    r2 = client.post(
        "/ncs",
        json={"supplier_id": bad_supplier_id, "severity": "low", "description": "x"},
        headers=headers_q,
    )
    assert r2.status_code == 400, r2.text

    # 3) Outbox must remain empty (no pending events written)
    with get_session() as s:
        assert s.query(OutboxEvent).count() == 0
