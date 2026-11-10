from unittest.mock import patch

import pytest


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
async def test_logout_redirect_to_homepage_when_public(auth_client):
    res = await auth_client.get("/auth/logout", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers.get("location") == "/"


@pytest.mark.asyncio
async def test_logout_redirect_to_login_when_locked(auth_client):
    with patch("server.api.auth.REQUIRE_AUTH_FOR_HOMEPAGE", True):
        res = await auth_client.get("/auth/logout", follow_redirects=False)
        assert res.status_code == 303
        assert "/login" in res.headers.get("location", "")


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


@pytest.mark.asyncio
async def test_auth_config_default_public_homepage(client):
    res = await client.get("/auth/config")
    assert res.status_code == 200
    data = res.json()
    assert "require_auth_for_homepage" in data
    assert data["require_auth_for_homepage"] is False


@pytest.mark.asyncio
async def test_auth_config_locked_toggle(client):
    with patch("server.api.auth.REQUIRE_AUTH_FOR_HOMEPAGE", True):
        res = await client.get("/auth/config")
        assert res.status_code == 200
        data = res.json()
        assert data["require_auth_for_homepage"] is True


@pytest.mark.asyncio
async def test_open_redirect_protection_on_logout(auth_client):
    """Ensure malicious redirect targets are sanitized to internal paths."""
    res = await auth_client.get("/auth/logout?next=https://evil.com", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers.get("location") == "/"

    res2 = await auth_client.get("/auth/logout?next=//evil.com/path", follow_redirects=False)
    assert res2.status_code == 303
    assert res2.headers.get("location") == "/"


@pytest.mark.asyncio
async def test_login_auth_error_generic_detail_and_exception_chaining(client):
    from server.auth.bridge import AuthError

    with patch("server.api.auth.authenticate_user", side_effect=AuthError("PAM verification internal secret")):
        res = await client.post("/auth/login", json={"username": "alice", "password": "wrong"})
        assert res.status_code == 401
        data = res.json()
        assert data["detail"] == "Invalid username or password"
        assert "PAM" not in data["detail"]


@pytest.mark.asyncio
async def test_login_redirect_uses_safe_next(client):
    mock_user = {"uid": 1000, "gid": 1000, "gids": [1000], "shell": "/bin/bash", "home": "/home/alice"}
    with patch("server.api.auth.authenticate_user", return_value=mock_user):
        res = await client.post(
            "/auth/login",
            json={"username": "alice", "password": "password", "next": "/overview"},
        )
        assert res.status_code == 200
        assert res.json()["redirect"] == "/overview"

