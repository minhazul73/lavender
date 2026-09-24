import pytest


@pytest.mark.asyncio
async def test_get_device_info(client):
    res = await client.get("/api/device/info")
    assert res.status_code == 200
    data = res.json()
    assert "hostname" in data
    assert "kernel" in data
    assert "model" in data
    assert "arch" in data


@pytest.mark.asyncio
async def test_get_device_battery(client, mock_sysfs):
    res = await client.get("/api/device/battery")
    assert res.status_code == 200
    data = res.json()
    assert "battery" in data
    assert "thermal" in data
    assert "cpu_freq" in data
    assert "uptime" in data
