from __future__ import annotations

def test_healthz_sets_request_id_header(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert "X-Request-ID" in r.headers
    assert r.headers["X-Request-ID"]
