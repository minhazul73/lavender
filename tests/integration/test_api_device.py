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
    assert data.get("app_version") == "0.5.0"


@pytest.mark.asyncio
async def test_get_device_battery(client, mock_sysfs):
    res = await client.get("/api/device/battery")
    assert res.status_code == 200
    data = res.json()
    assert "battery" in data
    assert "thermal" in data
    assert "cpu_freq" in data
    assert "uptime" in data


@pytest.mark.asyncio
async def test_sse_generator_initial_burst(mock_sysfs):
    import json
    from server.api.live import sse_generator

    gen = sse_generator(["cpu", "ram", "network"])
    events = []
    for _ in range(3):
        item = await gen.__anext__()
        events.append(item)
    await gen.aclose()

    metrics = [json.loads(e.replace("data: ", "").strip())["metric"] for e in events]
    assert "cpu" in metrics
    assert "ram" in metrics
    assert "network" in metrics
