import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_get_packages_and_legacy_alias(auth_client):
    with patch("server.api.packages.get_installed_packages", return_value=[{"name": "curl", "version": "8.8"}]), \
         patch("server.api.packages.get_upgradable_packages", return_value=[]):
        res1 = await auth_client.get("/api/packages?refresh=false&include_list=true")
        assert res1.status_code == 200
        assert "backend" in res1.json()

        res2 = await auth_client.get("/api/device/packages?refresh=false&include_list=true")
        assert res2.status_code == 200
        assert "backend" in res2.json()


@pytest.mark.asyncio
async def test_packages_search_and_legacy_alias(auth_client):
    with patch("server.api.packages.search_packages", return_value=[{"name": "git", "description": "VCS"}]):
        res1 = await auth_client.get("/api/packages/search?query=git")
        assert res1.status_code == 200
        assert len(res1.json()["results"]) == 1

        res2 = await auth_client.get("/api/device/packages/search?query=git")
        assert res2.status_code == 200
        assert len(res2.json()["results"]) == 1


@pytest.mark.asyncio
async def test_packages_upgrade_admin_gate(auth_client, admin_client):
    res_forbidden = await auth_client.post("/api/packages/upgrade")
    assert res_forbidden.status_code == 403

    with patch("server.api.packages.run_sudo_async", return_value=(0, "Upgraded successfully", "")):
        res_ok = await admin_client.post("/api/packages/upgrade")
        assert res_ok.status_code == 200
        assert res_ok.json()["success"] is True
