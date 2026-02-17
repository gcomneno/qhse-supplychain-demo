# tests/test_auth_smoke.py

from __future__ import annotations

from tests.utils_auth import auth_headers, login_and_get_token


def test_login_invalid(client):
    resp = client.post(
        "/auth/login",
        json={"username": "quality", "password": "wrong"},
    )
    assert resp.status_code == 401, resp.text


def test_kpi_access_authorized(client):
    token = login_and_get_token(client, "quality", "quality")
    resp = client.get(
        "/kpi",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


def test_kpi_forbidden_procurement(client):
    token = login_and_get_token(client, "procurement", "procurement")
    resp = client.get(
        "/kpi",
        headers=auth_headers(token),
    )
    assert resp.status_code == 403, resp.text


def test_suppliers_write_forbidden_quality(client):
    token = login_and_get_token(client, "quality", "quality")
    resp = client.post(
        "/suppliers",
        json={"name": "ACME", "certification_expiry": None},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403, resp.text


def test_suppliers_write_allowed_procurement(client):
    token = login_and_get_token(client, "procurement", "procurement")
    resp = client.post(
        "/suppliers",
        json={"name": "ACME", "certification_expiry": None},
        headers=auth_headers(token),
    )
    assert resp.status_code in (200, 201), resp.text
