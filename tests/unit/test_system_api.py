"""
Unit tests for dashboard/api/system.py endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from dashboard.main import app
from dashboard.auth.session import session_store
from dashboard.config import SESSION_COOKIE_NAME


@pytest_asyncio.fixture
async def auth_session():
    """Create an authenticated session."""
    session = await session_store.create(
        "testuser",
        {
            "uid": 1000,
            "gid": 1000,
            "home": "/home/testuser",
            "shell": "/bin/bash",
            "groups": ["wheel", "sudo"],
        },
    )
    yield session
    await session_store.delete(session.session_id)


@pytest_asyncio.fixture
async def admin_session():
    """Create an elevated admin session."""
    session = await session_store.create(
        "adminuser",
        {
            "uid": 0,
            "gid": 0,
            "home": "/root",
            "shell": "/bin/bash",
            "groups": ["root", "wheel", "sudo"],
        },
    )
    session.elevate()
    yield session
    await session_store.delete(session.session_id)


@pytest.mark.asyncio
async def test_system_storage_public():
    """Test /api/system/storage is public."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/storage")
        assert response.status_code == 200
        data = response.json()
        assert "disks" in data


@pytest.mark.asyncio
async def test_system_memory_public():
    """Test /api/system/memory is public."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/memory")
        assert response.status_code == 200
        data = response.json()
        assert "human" in data
        assert "raw" in data


@pytest.mark.asyncio
async def test_system_logs_public():
    """Test /api/system/logs is public."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/logs?lines=5")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "count" in data


@pytest.mark.asyncio
async def test_system_logs_invalid_lines():
    """Test /api/system/logs with invalid lines param returns 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/logs?lines=0")
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_system_processes_public():
    """Test /api/system/processes is public."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/processes")
        assert response.status_code == 200
        data = response.json()
        assert "processes" in data
        assert "load" in data
        assert "memory" in data


@pytest.mark.asyncio
async def test_system_processes_with_params():
    """Test /api/system/processes with sort and limit params."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/processes?sort_by=cpu&limit=10")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_system_processes_invalid_sort():
    """Test /api/system/processes with invalid sort_by returns 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/processes?sort_by=invalid")
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_system_services_public():
    """Test /api/system/services is public."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/services")
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert "count" in data


@pytest.mark.asyncio
async def test_system_services_with_scope():
    """Test /api/system/services with scope param."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/services?scope=system")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_system_service_status_public(auth_session):
    """Test /api/system/services/{name} requires auth."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Should redirect or 401
        response = await client.get("/api/system/services/sshd.service")
        assert response.status_code in (307, 401)


@pytest.mark.asyncio
async def test_system_service_status_authenticated(auth_session):
    """Test /api/system/services/{name} with auth."""
    token = session_store.sign_session_id(auth_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.system.get_service_status") as mock_status:
            mock_status.return_value = {"name": "sshd", "active": True}
            response = await client.get("/api/system/services/sshd.service")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_system_service_logs_requires_auth():
    """Test /api/system/services/{name}/logs requires auth."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/system/services/sshd.service/logs")
        assert response.status_code in (307, 401)


@pytest.mark.asyncio
async def test_system_service_action_requires_auth():
    """Test /api/system/services/{name}/{action} requires auth."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/system/services/sshd.service/start")
        assert response.status_code in (307, 401)


@pytest.mark.asyncio
async def test_system_service_action_invalid_action(auth_session):
    """Test service action with invalid action returns 400."""
    token = session_store.sign_session_id(auth_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        response = await client.post("/api/system/services/sshd.service/invalid")
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_system_service_action_system_requires_admin(auth_session):
    """Test system service action requires admin for non-elevated user."""
    token = session_store.sign_session_id(auth_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        response = await client.post("/api/system/services/sshd.service/start")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_system_service_action_user_service(auth_session):
    """Test user service action works for authenticated user."""
    token = session_store.sign_session_id(auth_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.system.run_user_service_async") as mock_run:
            mock_run.return_value = (0, "Started", "")
            response = await client.post(
                "/api/system/services/user-test.service/start?user=true"
            )
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_system_service_action_system_admin(admin_session):
    """Test system service action works for admin."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.system.run_sudo_async") as mock_run:
            mock_run.return_value = (0, "Started", "")
            response = await client.post("/api/system/services/sshd.service/start")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_system_kill_process_requires_admin(auth_session):
    """Test /api/system/processes/kill requires admin."""
    token = session_store.sign_session_id(auth_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        response = await client.post("/api/system/processes/kill?pid=1234")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_system_kill_process_admin(admin_session):
    """Test kill process with admin."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.system.run_sudo_async") as mock_run:
            mock_run.return_value = (0, "Killed", "")
            response = await client.post("/api/system/processes/kill?pid=1234")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_system_kill_process_invalid_pid(admin_session):
    """Test kill process with invalid PID returns 422."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        response = await client.post("/api/system/processes/kill?pid=0")
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_system_storage_empty_disks():
    """Test storage API when no disks found."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch("dashboard.api.system.get_disk_usage") as mock_disks:
            mock_disks.return_value = []
            response = await client.get("/api/system/storage")
            assert response.status_code == 200
            data = response.json()
            assert data["disks"] == []


@pytest.mark.asyncio
async def test_system_logs_empty():
    """Test logs API when no logs found."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch("dashboard.api.system.get_recent_logs") as mock_logs:
            mock_logs.return_value = []
            response = await client.get("/api/system/logs?lines=5")
            assert response.status_code == 200
            data = response.json()
            assert data["logs"] == []
            assert data["count"] == 0


@pytest.mark.asyncio
async def test_system_services_empty():
    """Test services API when no services found."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch("dashboard.api.system.list_services") as mock_list:
            mock_list.return_value = []
            response = await client.get("/api/system/services")
            assert response.status_code == 200
            data = response.json()
            assert data["services"] == []
            assert data["count"] == 0


@pytest.mark.asyncio
async def test_system_service_action_failure(admin_session):
    """Test service action failure returns 500."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.system.run_sudo_async") as mock_run:
            mock_run.return_value = (1, "", "Failed to start")
            response = await client.post("/api/system/services/sshd.service/start")
            assert response.status_code == 500


@pytest.mark.asyncio
async def test_system_kill_process_failure(admin_session):
    """Test kill process failure returns 500."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.system.run_sudo_async") as mock_run:
            mock_run.return_value = (1, "", "No such process")
            response = await client.post("/api/system/processes/kill?pid=99999")
            assert response.status_code == 500
