from __future__ import annotations

from tests.utils_auth import auth_headers, login_and_get_token


def test_ncs_filters_status_and_severity(client):
    # create supplier (procurement)
    tp = login_and_get_token(client, "procurement", "procurement")
    r1 = client.post(
        "/suppliers",
        json={"name": "ACME", "certification_expiry": None},
        headers=auth_headers(tp),
    )
    assert r1.status_code in (200, 201), r1.text
    supplier_id = r1.json()["id"]

    # create 3 NCs (quality)
    tq = login_and_get_token(client, "quality", "quality")
    for sev in ["low", "high", "high"]:
        r = client.post(
            "/ncs",
            json={"supplier_id": supplier_id, "severity": sev, "description": f"nc-{sev}"},
            headers=auth_headers(tq),
        )
        assert r.status_code == 201, r.text

    # close the first NC (quality) so we have CLOSED + OPEN mixed
    # Take list (auditor) and close the first returned id
    ta = login_and_get_token(client, "auditor", "auditor")
    rlist = client.get("/ncs", headers=auth_headers(ta))
    assert rlist.status_code == 200, rlist.text
    ncs = rlist.json()
    assert len(ncs) >= 3
    first_id = ncs[0]["id"]

    rclose = client.patch(f"/ncs/{first_id}/close", headers=auth_headers(tq))
    assert rclose.status_code == 200, rclose.text

    # Filter by severity=high (auditor read)
    rh = client.get("/ncs?severity=high", headers=auth_headers(ta))
    assert rh.status_code == 200, rh.text
    highs = rh.json()
    assert all(x["severity"] == "high" for x in highs)

    # Filter by status=CLOSED
    rc = client.get("/ncs?status=CLOSED", headers=auth_headers(ta))
    assert rc.status_code == 200, rc.text
    closeds = rc.json()
    assert all(x["status"] == "CLOSED" for x in closeds)
    assert len(closeds) >= 1

    # Combined filter: status=OPEN&severity=high
    roh = client.get("/ncs?status=OPEN&severity=high", headers=auth_headers(ta))
    assert roh.status_code == 200, roh.text
    open_high = roh.json()
    assert all((x["status"] == "OPEN" and x["severity"] == "high") for x in open_high)
