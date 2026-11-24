import asyncio

import pytest


@pytest.mark.asyncio
async def test_api_network_uses_to_thread(auth_client, monkeypatch):
    calls = []
    real_to_thread = asyncio.to_thread

    async def tracking_to_thread(func, *args, **kwargs):
        calls.append(getattr(func, "__name__", str(func)))
        return await real_to_thread(func, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", tracking_to_thread)

    res = await auth_client.get("/api/network")
    assert res.status_code == 200

    assert "get_dns_info" in calls
    assert "get_network_summary" in calls
    assert "get_ip_addresses" in calls
    assert "get_wifi_info" in calls
    assert "get_gateways" in calls
