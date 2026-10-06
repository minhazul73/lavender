"""
Integration tests for Lavender API endpoints using httpx.AsyncClient.
"""
import pytest
from httpx import AsyncClient, ASGITransport
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
