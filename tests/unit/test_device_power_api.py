"""
Unit tests for dashboard/api/device.py — power control endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from dashboard.main import app
from dashboard.auth.session import session_store
from dashboard.config import SESSION_COOKIE_NAME


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
async def test_device_power_state_public():
    """Test /api/device/power/state is public."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/device/power/state")
        assert response.status_code == 200
        data = response.json()
        assert "active_governor" in data
        assert "available_governors" in data
        assert "scheduled" in data


@pytest.mark.asyncio
async def test_device_reboot_requires_admin():
    """Test /api/device/power/reboot requires admin."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/device/power/reboot")
        assert response.status_code in (307, 401, 403)


@pytest.mark.asyncio
async def test_device_reboot_admin(admin_session):
    """Test reboot with admin privileges."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.device.run_sudo_async") as mock_run:
            mock_run.return_value = (0, "Rebooting", "")
            response = await client.post("/api/device/power/reboot")
            assert response.status_code == 200
            data = response.json()
            assert data["action"] == "reboot"
            assert data["success"] is True


@pytest.mark.asyncio
async def test_device_reboot_admin_failure(admin_session):
    """Test reboot failure returns 500."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.device.run_sudo_async") as mock_run:
            mock_run.return_value = (1, "", "Interactive authentication required")
            response = await client.post("/api/device/power/reboot")
            assert response.status_code == 500


@pytest.mark.asyncio
async def test_device_poweroff_requires_admin():
    """Test /api/device/power/poweroff requires admin."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/device/power/poweroff")
        assert response.status_code in (307, 401, 403)


@pytest.mark.asyncio
async def test_device_poweroff_admin(admin_session):
    """Test poweroff with admin privileges."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.device.run_sudo_async") as mock_run:
            mock_run.return_value = (0, "Powering off", "")
            response = await client.post("/api/device/power/poweroff")
            assert response.status_code == 200
            data = response.json()
            assert data["action"] == "poweroff"


@pytest.mark.asyncio
async def test_device_poweroff_admin_failure(admin_session):
    """Test poweroff failure returns 500."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.device.run_sudo_async") as mock_run:
            mock_run.return_value = (1, "", "Failed to power off")
            response = await client.post("/api/device/power/poweroff")
            assert response.status_code == 500


@pytest.mark.asyncio
async def test_device_suspend_requires_admin():
    """Test /api/device/power/suspend requires admin."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/device/power/suspend")
        assert response.status_code in (307, 401, 403)


@pytest.mark.asyncio
async def test_device_suspend_admin(admin_session):
    """Test suspend with admin privileges."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.device.run_sudo_async") as mock_run:
            mock_run.return_value = (0, "Suspending", "")
            response = await client.post("/api/device/power/suspend")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_device_suspend_admin_failure(admin_session):
    """Test suspend failure returns 500."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.device.run_sudo_async") as mock_run:
            mock_run.return_value = (1, "", "Suspend failed")
            response = await client.post("/api/device/power/suspend")
            assert response.status_code == 500


@pytest.mark.asyncio
async def test_device_schedule_power_requires_admin():
    """Test /api/device/power/schedule requires admin."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/device/power/schedule", json={"action": "reboot", "minutes": 5}
        )
        assert response.status_code in (307, 401, 403)


@pytest.mark.asyncio
async def test_device_schedule_power_invalid_action(admin_session):
    """Test schedule with invalid action returns 400."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        response = await client.post(
            "/api/device/power/schedule", json={"action": "invalid", "minutes": 5}
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_device_schedule_power_invalid_minutes(admin_session):
    """Test schedule with invalid minutes returns 400."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        response = await client.post(
            "/api/device/power/schedule", json={"action": "reboot", "minutes": 0}
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_device_schedule_power_success(admin_session):
    """Test schedule power action succeeds."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.device.schedule_power_action") as mock_sched:
            mock_sched.return_value = {
                "success": True,
                "action": "reboot",
                "minutes": 5,
            }
            response = await client.post(
                "/api/device/power/schedule",
                json={"action": "reboot", "minutes": 5, "message": "Test"},
            )
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_device_cancel_scheduled_requires_admin():
    """Test /api/device/power/cancel-scheduled requires admin."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/device/power/cancel-scheduled")
        assert response.status_code in (307, 401, 403)


@pytest.mark.asyncio
async def test_device_cancel_scheduled_success(admin_session):
    """Test cancel scheduled power action succeeds."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.device.cancel_scheduled_action") as mock_cancel:
            mock_cancel.return_value = {"success": True}
            response = await client.post("/api/device/power/cancel-scheduled")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_device_set_governor_requires_admin():
    """Test /api/device/power/governor requires admin."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/device/power/governor?governor=conservative")
        assert response.status_code in (307, 401, 403)


@pytest.mark.asyncio
async def test_device_set_governor_success(admin_session):
    """Test set CPU governor with admin privileges."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.device.set_cpu_governor") as mock_gov:
            mock_gov.return_value = {"success": True, "governor": "conservative"}
            response = await client.post(
                "/api/device/power/governor?governor=conservative"
            )
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_device_set_governor_failure(admin_session):
    """Test set CPU governor with invalid governor returns 400."""
    token = session_store.sign_session_id(admin_session.session_id)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        with patch("dashboard.api.device.set_cpu_governor") as mock_gov:
            mock_gov.return_value = {
                "success": False,
                "error": "Governor 'invalid' not supported",
            }
            response = await client.post("/api/device/power/governor?governor=invalid")
            assert response.status_code == 400
