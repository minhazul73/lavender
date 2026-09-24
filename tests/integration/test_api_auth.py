import pytest
from unittest.mock import patch
from server.core.config import SESSION_COOKIE_NAME


@pytest.mark.asyncio
async def test_auth_me_authenticated(auth_client, regular_session):
    res = await auth_client.get("/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == regular_session.username
    assert data["uid"] == 1000
    assert data["is_admin"] is False


@pytest.mark.asyncio
async def test_unauthenticated_protected_endpoint(client):
    res = await client.get("/api/users")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_logout_endpoint(auth_client):
    res = await auth_client.post("/auth/logout", headers={"Accept": "application/json"})
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Subsequent request should be unauthorized
    me_res = await auth_client.get("/auth/me")
    assert me_res.status_code == 401


@pytest.mark.asyncio
async def test_elevation_flow(auth_client, regular_session):
    with patch("server.api.auth.verify_sudo_password", return_value=(True, "")):
        res = await auth_client.post("/auth/elevate", json={"password": "valid_sudo_pwd"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["is_admin"] is True

    # Profile now reflects administrative status
    profile_res = await auth_client.get("/auth/me")
    assert profile_res.json()["is_admin"] is True

    # Drop elevation
    with patch("server.api.auth.drop_sudo_ticket", return_value=True):
        drop_res = await auth_client.post("/auth/drop-admin")
        assert drop_res.status_code == 200
        assert drop_res.json()["is_admin"] is False
