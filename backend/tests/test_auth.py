"""Tests for the auth routes."""

from tests.conftest import auth_headers, register_user


async def test_register_and_login_success(client):
    data = await register_user(client)
    assert data["access_token"]
    assert data["user"]["email"] == "tester@example.com"
    assert data["user"]["points"] == 0

    # Login with the same credentials
    resp = await client.post(
        "/api/auth/login",
        json={"email": "tester@example.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_register_duplicate_email(client):
    await register_user(client)
    resp = await client.post(
        "/api/auth/register",
        json={"name": "Other", "email": "tester@example.com", "password": "secret456"},
    )
    assert resp.status_code == 400


async def test_login_wrong_password(client):
    await register_user(client)
    resp = await client.post(
        "/api/auth/login",
        json={"email": "tester@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401


async def test_me_requires_token(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_with_valid_token(client):
    data = await register_user(client)
    resp = await client.get("/api/auth/me", headers=auth_headers(data["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["email"] == "tester@example.com"