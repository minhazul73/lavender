"""
Integration tests for SPA serving, static assets, and fallback routing.
"""
import pytest


@pytest.mark.asyncio
async def test_homepage_renders_html(client):
    res = await client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "Lavender" in res.text


@pytest.mark.asyncio
async def test_login_page_renders_html(client):
    res = await client.get("/login")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "Lavender" in res.text or "Sign in" in res.text or "login" in res.text.lower()


@pytest.mark.asyncio
async def test_protected_pages_render_for_authenticated_user(auth_client):
    pages = [
        "/services",
        "/processes",
        "/storage",
        "/network",
        "/packages",
        "/users",
        "/power",
    ]
    for page in pages:
        res = await auth_client.get(page)
        assert res.status_code == 200, f"Page {page} failed to render: status {res.status_code}"
        assert "text/html" in res.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_spa_fallback_and_api_404(client):
    # Any frontend SPA subroute returns index.html
    res_spa = await client.get("/services/deep/route")
    assert res_spa.status_code == 200
    assert "text/html" in res_spa.headers.get("content-type", "")
    assert "Lavender" in res_spa.text

    # Unhandled API endpoints must return 404, not index.html
    res_api = await client.get("/api/nonexistent-endpoint")
    assert res_api.status_code == 404

    # Unhandled auth endpoints must return 404, not index.html
    res_auth = await client.get("/auth/nonexistent")
    assert res_auth.status_code == 404


@pytest.mark.asyncio
async def test_legacy_device_and_system_routes(client, auth_client):
    # Device info (public)
    res_info = await client.get("/api/device/info")
    assert res_info.status_code == 200
    assert res_info.headers.get("content-type", "").startswith("application/json")

    # System processes (authenticated)
    res_proc = await auth_client.get("/api/system/processes")
    assert res_proc.status_code == 200
    assert res_proc.headers.get("content-type", "").startswith("application/json")
