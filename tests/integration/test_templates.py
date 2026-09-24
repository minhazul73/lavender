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
    assert "Sign in" in res.text or "login" in res.text.lower()


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
async def test_legacy_device_and_system_routes(client, auth_client):
    # Device info (public)
    res_info = await client.get("/api/device/info")
    assert res_info.status_code == 200
    assert res_info.headers.get("content-type", "").startswith("application/json")

    # System processes (authenticated)
    res_proc = await auth_client.get("/api/system/processes")
    assert res_proc.status_code == 200
    assert res_proc.headers.get("content-type", "").startswith("application/json")
