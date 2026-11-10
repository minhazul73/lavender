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


@pytest.mark.asyncio
async def test_live_sse_returns_503_when_capacity_exceeded(client):
    from server.services.live import get_live_monitor
    from server.services.live_monitor import MAX_LIVE_CLIENTS

    monitor = get_live_monitor()
    initial_count = monitor._client_count
    try:
        monitor._client_count = MAX_LIVE_CLIENTS
        res = await client.get("/api/device/live")
        assert res.status_code == 503
        assert "Maximum live SSE clients reached" in res.json()["detail"]
    finally:
        monitor._client_count = initial_count


@pytest.mark.asyncio
async def test_live_sse_streaming_response_releases_on_completion():
    from unittest.mock import AsyncMock

    from server.api.live import SSEStreamingResponse

    mock_monitor = AsyncMock()

    async def sample_gen():
        yield b"data: test\n\n"

    resp = SSEStreamingResponse(sample_gen(), monitor=mock_monitor, media_type="text/event-stream")
    scope = {"type": "http", "asgi": {"spec_version": "2.1"}}

    async def receive():
        return {"type": "http.disconnect"}

    async def send(msg):
        pass

    await resp(scope, receive, send)
    mock_monitor.remove_client.assert_awaited_once()


@pytest.mark.asyncio
async def test_live_monitor_add_client_raises_live_capacity_error():
    from server.services.live import LiveCapacityError, LiveMonitor
    from server.services.live_monitor import MAX_LIVE_CLIENTS

    monitor = LiveMonitor()
    monitor._client_count = MAX_LIVE_CLIENTS
    with pytest.raises(LiveCapacityError, match="Maximum live SSE clients reached"):
        await monitor.add_client()


@pytest.mark.asyncio
async def test_live_sse_streaming_response_cleanup_failure_logged_and_preserves_error():
    from unittest.mock import AsyncMock, patch

    from server.api.live import SSEStreamingResponse

    mock_monitor = AsyncMock()
    mock_monitor.remove_client.side_effect = RuntimeError("cleanup database lock failed")

    async def failing_gen():
        raise ValueError("stream processing error")
        yield b"never"

    resp = SSEStreamingResponse(failing_gen(), monitor=mock_monitor, media_type="text/event-stream")
    scope = {"type": "http", "asgi": {"spec_version": "2.1"}}

    async def receive():
        return {"type": "http.disconnect"}

    async def send(msg):
        pass

    with patch("server.api.live.logger.exception") as mock_log:
        with pytest.raises(ValueError, match="stream processing error"):
            await resp(scope, receive, send)

        mock_log.assert_called_once_with("Failed to release SSE client capacity")



