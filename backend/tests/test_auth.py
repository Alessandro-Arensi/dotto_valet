import pytest
from tests.conftest import auth_headers


async def test_login_success(client, admin):
    r = await client.post("/api/auth/login", json={"phone": admin.phone, "pin": "1234"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["operator"]["is_admin"] is True


async def test_login_wrong_pin(client, admin):
    r = await client.post("/api/auth/login", json={"phone": admin.phone, "pin": "9999"})
    assert r.status_code == 401


async def test_login_inactive_operator(client, db_session, admin):
    admin.is_active = False
    await db_session.commit()
    r = await client.post("/api/auth/login", json={"phone": admin.phone, "pin": "1234"})
    assert r.status_code == 401


async def test_me_requires_auth(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 403  # HTTPBearer returns 403 when header absent


async def test_me_returns_operator(client, admin, admin_token):
    r = await client.get("/api/auth/me", headers=auth_headers(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Admin Test"
    assert body["is_admin"] is True
