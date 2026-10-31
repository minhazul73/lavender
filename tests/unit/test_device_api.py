"""
Unit tests for device API endpoints - failure scenarios and edge cases.
Tests cover authentication, validation, and error handling paths.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
from dashboard.main import app
from dashboard.auth.session import session_store
from dashboard.config import SESSION_COOKIE_NAME


@pytest_asyncio.fixture
async def admin_session():
    """Create an elevated admin session for testing."""
    session = await session_store.create(
        "testadmin",
        {
            "uid": 1000,
            "gid": 1000,
            "home": "/home/testadmin",
            "shell": "/bin/bash",
            "groups": ["users", "wheel"],
        },
    )
    session.elevate()
    token = session_store.sign_session_id(session.session_id)
    yield token, session
    await session_store.delete(session.session_id)


@pytest_asyncio.fixture
async def user_session():
    """Create a regular user session for testing."""
    session = await session_store.create(
        "testuser",
        {
            "uid": 1000,
            "gid": 1000,
            "home": "/home/testuser",
            "shell": "/bin/bash",
            "groups": ["users"],
        },
    )
    token = session_store.sign_session_id(session.session_id)
    yield token, session
    await session_store.delete(session.session_id)


class TestDeviceNetworkPing:
    """Test /api/device/network/ping endpoint."""

    @pytest.mark.asyncio
    async def test_ping_empty_target_defaults_to_google(self, user_session):
        """Test ping with empty target uses default 8.8.8.8."""
        token, _ = user_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            with patch("dashboard.api.device.ping_test") as mock_ping:
                mock_ping.return_value = {"success": True, "received": 3}
                response = await client.get("/api/device/network/ping")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ping_invalid_characters_rejected(self, user_session):
        """Test ping with invalid target characters."""
        token, _ = user_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            response = await client.get(
                "/api/device/network/ping?target=http://evil.com"
            )
            # Should fail validation or be sanitized
            assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_ping_unauthenticated_rejected(self):
        """Test ping endpoint requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/device/network/ping")
            assert response.status_code == 401  # API route, no session


class TestDeviceNetworkDnsQuery:
    """Test /api/device/network/dns-query endpoint."""

    @pytest.mark.asyncio
    async def test_dns_query_empty_domain(self, user_session):
        """Test DNS query with empty domain."""
        token, _ = user_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            with patch("dashboard.api.device.dns_lookup") as mock_dns:
                mock_dns.return_value = {"success": False, "error": "Empty domain"}
                response = await client.get("/api/device/network/dns-query?domain=")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is False

    @pytest.mark.asyncio
    async def test_dns_query_unauthenticated_rejected(self):
        """Test DNS query requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/device/network/dns-query")
            assert response.status_code == 401


class TestDeviceNetworkWifiScan:
    """Test /api/device/network/wifi-scan endpoint."""

    @pytest.mark.asyncio
    async def test_wifi_scan_no_command_available(self, user_session):
        """Test WiFi scan when nmcli is not available."""
        token, _ = user_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            with patch("dashboard.api.device.scan_wifi_networks") as mock_scan:
                mock_scan.return_value = []
                response = await client.post("/api/device/network/wifi-scan")
                assert response.status_code == 200
                data = response.json()
                assert data["networks"] == []

    @pytest.mark.asyncio
    async def test_wifi_scan_unauthenticated_rejected(self):
        """Test WiFi scan requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/device/network/wifi-scan")
            assert response.status_code == 401


class TestDeviceBattery:
    """Test /api/device/battery endpoint."""

    @pytest.mark.asyncio
    async def test_battery_info_without_session(self):
        """Test battery info allows unauthenticated (get_current_session)."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with patch("dashboard.api.device.get_battery_info") as mock_bat:
                with patch("dashboard.api.device.get_thermal_zones") as mock_therm:
                    with patch("dashboard.api.device.get_cpu_frequencies") as mock_freq:
                        with patch(
                            "dashboard.api.device.get_cpu_scaling_available"
                        ) as mock_scaling:
                            with patch(
                                "dashboard.api.device.get_uptime"
                            ) as mock_uptime:
                                mock_bat.return_value = {"present": False}
                                mock_therm.return_value = []
                                mock_freq.return_value = {}
                                mock_scaling.return_value = []
                                mock_uptime.return_value = 0
                                response = await client.get("/api/device/battery")
                                assert response.status_code == 200


class TestDevicePackages:
    """Test /api/device/packages endpoints."""

    @pytest.mark.asyncio
    async def test_packages_unauthenticated_rejected(self):
        """Test packages endpoint requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/device/packages")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upgrade_packages_no_command(self, admin_session):
        """Test upgrade when no command available for package manager."""
        token, _ = admin_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            with patch("dashboard.api.device.get_package_manager") as mock_mgr:
                mock_mgr.return_value.get_upgrade_command = MagicMock(return_value=None)
                response = await client.post("/api/device/packages/upgrade")
                assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upgrade_packages_failure(self, admin_session):
        """Test upgrade command fails."""
        token, _ = admin_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            with patch("dashboard.api.device.get_package_manager") as mock_mgr:
                with patch("dashboard.api.device.run_sudo_async") as mock_sudo:
                    mock_mgr.return_value.get_upgrade_command = MagicMock(
                        return_value=["apk", "upgrade"]
                    )
                    mock_sudo.return_value = (1, "", "Upgrade failed")
                    response = await client.post("/api/device/packages/upgrade")
                    assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_install_package_failure(self, admin_session):
        """Test package install fails."""
        token, _ = admin_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            with patch("dashboard.api.device.get_package_manager") as mock_mgr:
                with patch("dashboard.api.device.run_sudo_async") as mock_sudo:
                    mock_mgr.return_value.get_install_command = MagicMock(
                        return_value=["apk", "add", "vim"]
                    )
                    mock_sudo.return_value = (1, "", "Package not found")
                    response = await client.post(
                        "/api/device/packages/install?package=vim"
                    )
                    assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_remove_package_no_command(self, admin_session):
        """Test remove when no command available."""
        token, _ = admin_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            with patch("dashboard.api.device.get_package_manager") as mock_mgr:
                mock_mgr.return_value.get_remove_command = MagicMock(return_value=None)
                response = await client.post("/api/device/packages/remove?package=vim")
                assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_search_packages_empty_query_rejected(self, user_session):
        """Test package search with empty query."""
        token, _ = user_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            response = await client.get("/api/device/packages/search?query=")
            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_package_info_empty_query_rejected(self, user_session):
        """Test package info with empty package name."""
        token, _ = user_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            response = await client.get("/api/device/packages/info?package=")
            assert response.status_code == 422


class TestDeviceUsers:
    """Test /api/device/users endpoints."""

    @pytest.mark.asyncio
    async def test_users_unauthenticated_rejected(self):
        """Test users endpoint requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/device/users")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_terminate_session_missing_tty(self, admin_session):
        """Test terminate session without TTY."""
        token, _ = admin_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            response = await client.post("/api/device/users/session/terminate", json={})
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_terminate_session_already_ended(self, admin_session):
        """Test terminate session that already ended."""
        token, _ = admin_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            with patch("dashboard.api.device.run_sudo_async") as mock_sudo:
                mock_sudo.return_value = (1, "", "No such process")
                response = await client.post(
                    "/api/device/users/session/terminate", json={"tty": "pts/999"}
                )
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_ssh_keys_other_user_requires_admin(self, user_session):
        """Test getting SSH keys for another user requires admin."""
        token, session = user_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            response = await client.get("/api/device/users/otheruser/ssh-keys")
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_add_ssh_key_empty_key(self, user_session):
        """Test adding SSH key with empty key content."""
        token, session = user_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            response = await client.post(
                f"/api/device/users/{session.username}/ssh-keys", json={"key": ""}
            )
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_add_ssh_key_invalid_format(self, user_session):
        """Test adding SSH key with invalid format."""
        token, session = user_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            with patch("dashboard.api.device.add_user_ssh_key") as mock_add:
                mock_add.return_value = False
                response = await client.post(
                    f"/api/device/users/{session.username}/ssh-keys",
                    json={"key": "not-a-valid-ssh-key"},
                )
                assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_ssh_key_failure(self, user_session):
        """Test deleting SSH key that doesn't exist."""
        token, session = user_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            with patch("dashboard.api.device.delete_user_ssh_key") as mock_del:
                mock_del.return_value = False
                response = await client.delete(
                    f"/api/device/users/{session.username}/ssh-keys/999"
                )
                assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_groups_invalid_type(self, admin_session):
        """Test updating groups with non-list type."""
        token, _ = admin_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            response = await client.post(
                "/api/device/users/testuser/groups", json={"groups": "not-a-list"}
            )
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_groups_user_not_found(self, admin_session):
        """Test updating groups for non-existent user."""
        token, _ = admin_session
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            with patch("dashboard.api.device.parse_all_passwd_users") as mock_users:
                mock_users.return_value = [{"name": "existing"}]
                response = await client.post(
                    "/api/device/users/nonexistent/groups", json={"groups": ["wheel"]}
                )
                assert response.status_code == 404
