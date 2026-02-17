# tests/test_auth_smoke.py

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_token(username: str, password: str) -> str:
    resp = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_login_invalid():
    resp = client.post(
        "/auth/login",
        json={"username": "quality", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_kpi_access_authorized():
    token = get_token("quality", "quality")
    resp = client.get(
        "/kpi",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 404)


def test_kpi_forbidden_procurement():
    token = get_token("procurement", "procurement")
    resp = client.get(
        "/kpi",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_suppliers_write_forbidden_quality():
    token = get_token("quality", "quality")
    resp = client.post(
        "/suppliers",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_suppliers_write_allowed_procurement():
    token = get_token("procurement", "procurement")
    resp = client.post(
        "/suppliers",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201, 422)
