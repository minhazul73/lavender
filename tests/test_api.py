"""
Integration tests for Lavender API endpoints using httpx.AsyncClient.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from dashboard.main import app


@pytest.mark.asyncio
async def test_homepage_public_access():
    """Test public access to homepage '/'."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "Lavender" in response.text or "html" in response.text.lower()


@pytest.mark.asyncio
async def test_device_info_api():
    """Test /api/device/info endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/device/info")
        assert response.status_code == 200
        data = response.json()
        assert "model" in data
        assert "os_name" in data
        assert "kernel" in data


@pytest.mark.asyncio
async def test_system_storage_api():
    """Test /api/system/storage endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/storage")
        assert response.status_code == 200
        data = response.json()
        assert "disks" in data


@pytest.mark.asyncio
async def test_system_memory_api():
    """Test /api/system/memory endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/memory")
        assert response.status_code == 200
        data = response.json()
        assert "human" in data
        assert "raw" in data


@pytest.mark.asyncio
async def test_login_page_public_access():
    """Test public access to /login page."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/login")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_protected_route_redirects_unauthenticated():
    """Test accessing protected route without auth redirects to /login."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/services", follow_redirects=False)
        assert response.status_code == 307
        assert "/login" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_system_logs_api():
    """Test /api/system/logs endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/logs?lines=5")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "count" in data
        assert isinstance(data["logs"], list)


@pytest.mark.asyncio
async def test_login_json_payload_invalid():
    """Test /api/auth/login with invalid JSON returns 400."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/auth/login",
            headers={"Content-Type": "application/json"},
            content="not-valid-json",
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_json_empty_credentials():
    """Test /auth/login with empty username/password returns 400 for JSON."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/auth/login",
            headers={"Content-Type": "application/json"},
            json={"username": "", "password": ""},
        )
        assert response.status_code == 400
        assert "detail" in response.json()


@pytest.mark.asyncio
async def test_login_json_auth_failure():
    """Test /api/auth/login with invalid credentials returns 401 for JSON."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:

        with patch("dashboard.api.auth.authenticate_user") as mock_auth:
            from dashboard.auth.bridge import AuthError

            mock_auth.side_effect = AuthError("Invalid credentials")
            response = await client.post(
                "/auth/login",
                headers={"Content-Type": "application/json"},
                json={"username": "testuser", "password": "wrongpass"},
            )
            assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_form_auth_failure_redirects():
    """Test /api/auth/login with form data and invalid credentials
    redirects to login with error."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:

        with patch("dashboard.api.auth.authenticate_user") as mock_auth:
            from dashboard.auth.bridge import AuthError

            mock_auth.side_effect = AuthError("Invalid credentials")
            response = await client.post(
                "/auth/login", data={"username": "testuser", "password": "wrongpass"}
            )
            assert response.status_code == 303
            assert "error" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_auth_me_returns_profile():
    """Test /auth/me returns session profile for valid signed cookie."""
    from dashboard.auth.session import session_store
    from dashboard.config import SESSION_COOKIE_NAME

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        session = await session_store.create(
            "testuser",
            {
                "uid": 1000,
                "gid": 1000,
                "home": "/home/testuser",
                "shell": "/bin/bash",
                "groups": ["users", "wheel"],
            },
        )
        token = session_store.sign_session_id(session.session_id)
        client.cookies.set(SESSION_COOKIE_NAME, token)
        try:
            response = await client.get("/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["can_elevate"] is True
        finally:
            await session_store.delete(session.session_id)


@pytest.mark.asyncio
async def test_auth_me_unauthenticated_redirects():
    """Test /auth/me without session redirects to login (HTML) or 401 (API).

    /auth/me is served by the auth router (prefix /auth, no /api),
    so require_session treats it as an HTML request and returns 307
    redirect to /login regardless of Accept header.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/auth/me", headers={"Accept": "application/json"})
        assert response.status_code == 307
        assert "/login" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_auth_elevate_empty_password():
    """Test /auth/elevate with empty password returns 400."""
    from dashboard.auth.session import session_store
    from dashboard.config import SESSION_COOKIE_NAME

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        session = await session_store.create(
            "testuser",
            {
                "uid": 1000,
                "gid": 1000,
                "home": "/home/testuser",
                "shell": "/bin/bash",
                "groups": ["users", "wheel"],
            },
        )
        token = session_store.sign_session_id(session.session_id)
        client.cookies.set(SESSION_COOKIE_NAME, token)
        try:
            response = await client.post("/auth/elevate", json={"password": ""})
            assert response.status_code == 400
        finally:
            await session_store.delete(session.session_id)


@pytest.mark.asyncio
async def test_auth_elevate_wrong_password():
    """Test /auth/elevate with invalid sudo password returns 400."""
    from dashboard.auth.session import session_store
    from dashboard.config import SESSION_COOKIE_NAME

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        session = await session_store.create(
            "testuser",
            {
                "uid": 1000,
                "gid": 1000,
                "home": "/home/testuser",
                "shell": "/bin/bash",
                "groups": ["users", "wheel"],
            },
        )
        token = session_store.sign_session_id(session.session_id)
        client.cookies.set(SESSION_COOKIE_NAME, token)
        try:
            with patch("dashboard.api.auth.verify_sudo_password") as mock_verify:
                mock_verify.return_value = (False, "Invalid password")
                response = await client.post(
                    "/auth/elevate", json={"password": "wrongpass"}
                )
                assert response.status_code == 400
        finally:
            await session_store.delete(session.session_id)


@pytest.mark.asyncio
async def test_auth_elevate_success():
    """Test /auth/elevate with valid sudo password elevates session."""
    from dashboard.auth.session import session_store
    from dashboard.config import SESSION_COOKIE_NAME

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        session = await session_store.create(
            "testuser",
            {
                "uid": 1000,
                "gid": 1000,
                "home": "/home/testuser",
                "shell": "/bin/bash",
                "groups": ["users", "wheel"],
            },
        )
        token = session_store.sign_session_id(session.session_id)
        client.cookies.set(SESSION_COOKIE_NAME, token)
        try:
            with patch("dashboard.api.auth.verify_sudo_password") as mock_verify:
                mock_verify.return_value = (True, None)
                response = await client.post(
                    "/auth/elevate", json={"password": "correctpass"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["is_admin"] is True
                assert "expires_in" in data
        finally:
            await session_store.delete(session.session_id)


@pytest.mark.asyncio
async def test_auth_drop_admin():
    """Test /auth/drop-admin revokes elevation."""
    from dashboard.auth.session import session_store
    from dashboard.config import SESSION_COOKIE_NAME

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        session = await session_store.create(
            "testuser",
            {
                "uid": 1000,
                "gid": 1000,
                "home": "/home/testuser",
                "shell": "/bin/bash",
                "groups": ["users", "wheel"],
            },
        )
        session.elevate()
        token = session_store.sign_session_id(session.session_id)
        client.cookies.set(SESSION_COOKIE_NAME, token)
        try:
            with patch("dashboard.api.auth.drop_sudo_ticket") as mock_drop:
                mock_drop.return_value = None
                response = await client.post("/auth/drop-admin")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["is_admin"] is False
        finally:
            await session_store.delete(session.session_id)


@pytest.mark.asyncio
async def test_auth_logout_redirects():
    """Test /auth/logout (HTML) redirects to login."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/auth/logout")
        assert response.status_code == 303
        assert "Logged+out" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_auth_logout_json_post():
    """Test /auth/logout (JSON POST) returns success."""

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/auth/logout", headers={"Accept": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
