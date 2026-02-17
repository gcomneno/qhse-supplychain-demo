from __future__ import annotations

from tests.utils_auth import auth_headers, login_and_get_token


def test_list_suppliers_pagination(client):
    token_p = login_and_get_token(client, "procurement", "procurement")
    headers_p = auth_headers(token_p)

    # create 3 suppliers
    for i in range(3):
        r = client.post(
            "/suppliers",
            json={"name": f"ACME-{i}", "certification_expiry": None},
            headers=headers_p,
        )
        assert r.status_code in (200, 201), r.text

    token_a = login_and_get_token(client, "auditor", "auditor")
    headers_a = auth_headers(token_a)

    r_list = client.get("/suppliers?limit=2&offset=0", headers=headers_a)
    assert r_list.status_code == 200, r_list.text
    data = r_list.json()
    assert isinstance(data, list)
    assert len(data) == 2

    r_list_2 = client.get("/suppliers?limit=2&offset=2", headers=headers_a)
    assert r_list_2.status_code == 200, r_list_2.text
    data2 = r_list_2.json()
    assert isinstance(data2, list)
    assert len(data2) == 1


def test_list_ncs_pagination(client):
    token_p = login_and_get_token(client, "procurement", "procurement")
    headers_p = auth_headers(token_p)

    # create supplier
    r1 = client.post(
        "/suppliers",
        json={"name": "ACME", "certification_expiry": None},
        headers=headers_p,
    )
    assert r1.status_code in (200, 201), r1.text
    supplier_id = r1.json()["id"]

    token_q = login_and_get_token(client, "quality", "quality")
    headers_q = auth_headers(token_q)

    # create 3 NCs
    for i in range(3):
        r = client.post(
            "/ncs",
            json={"supplier_id": supplier_id, "severity": "low", "description": f"nc-{i}"},
            headers=headers_q,
        )
        assert r.status_code == 201, r.text

    token_a = login_and_get_token(client, "auditor", "auditor")
    headers_a = auth_headers(token_a)

    r_list = client.get("/ncs?limit=2&offset=0", headers=headers_a)
    assert r_list.status_code == 200, r_list.text
    data = r_list.json()
    assert isinstance(data, list)
    assert len(data) == 2

    r_list_2 = client.get("/ncs?limit=2&offset=2", headers=headers_a)
    assert r_list_2.status_code == 200, r_list_2.text
    data2 = r_list_2.json()
    assert isinstance(data2, list)
    assert len(data2) == 1
