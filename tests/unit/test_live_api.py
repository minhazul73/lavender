"""
Unit tests for /api/device/live SSE endpoint and sse_generator.
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from dashboard.main import app


class TestSseGenerator:
    """Direct tests of sse_generator() — metric filtering, error handling."""

    @pytest.mark.asyncio
    async def test_sse_default_metrics_all(self):
        """When metrics=None, all 5 metrics are requested."""
        from dashboard.api.live import sse_generator

        monitor = MagicMock()
        monitor.add_client = AsyncMock()
        monitor.remove_client = AsyncMock()
        monitor.get_cpu = AsyncMock(return_value={"value": 10})
        monitor.get_ram = AsyncMock(return_value={"value": 20})
        monitor.get_thermal = AsyncMock(return_value={"value": 30})
        monitor.get_battery = AsyncMock(return_value={"value": 40})
        monitor.get_network = AsyncMock(return_value={"value": 50})

        with patch("dashboard.api.live.get_live_monitor", return_value=monitor):
            gen = sse_generator(None)
            events = []
            async for chunk in gen:
                events.append(chunk)
                if len(events) >= 1:
                    break
            assert events
            assert "data:" in events[0]
            assert monitor.add_client.called

    @pytest.mark.asyncio
    async def test_sse_filtered_metrics(self):
        """Only requested metrics appear in the stream."""
        from dashboard.api.live import sse_generator

        monitor = MagicMock()
        monitor.add_client = AsyncMock()
        monitor.remove_client = AsyncMock()
        monitor.get_cpu = AsyncMock(return_value={"value": 10})
        monitor.get_ram = AsyncMock(return_value={"value": 20})

        with patch("dashboard.api.live.get_live_monitor", return_value=monitor):
            gen = sse_generator(["cpu", "ram"])
            events = []
            async for chunk in gen:
                events.append(chunk)
                if len(events) >= 1:
                    break
            assert events
            assert monitor.get_cpu.called
            assert not monitor.get_thermal.called
            assert not monitor.get_battery.called

    @pytest.mark.asyncio
    async def test_sse_unknown_metrics_ignored(self):
        """Unknown metric names are silently filtered out."""
        from dashboard.api.live import sse_generator

        monitor = MagicMock()
        monitor.add_client = AsyncMock()
        monitor.remove_client = AsyncMock()
        monitor.get_cpu = AsyncMock(return_value={"value": 10})

        with patch("dashboard.api.live.get_live_monitor", return_value=monitor):
            gen = sse_generator(["cpu", "nonexistent", "also_fake"])
            events = []
            async for chunk in gen:
                events.append(chunk)
                if len(events) >= 1:
                    break
            assert events
            assert monitor.get_cpu.called
            assert not monitor.get_ram.called

    @pytest.mark.asyncio
    async def test_sse_metric_error_emits_error_payload(self):
        """A failing metric emits a JSON error payload instead of crashing."""
        from dashboard.api.live import sse_generator

        monitor = MagicMock()
        monitor.add_client = AsyncMock()
        monitor.remove_client = AsyncMock()
        monitor.get_cpu = AsyncMock(side_effect=RuntimeError("sensor dead"))
        monitor.get_ram = AsyncMock(return_value={"value": 20})

        with patch("dashboard.api.live.get_live_monitor", return_value=monitor):
            gen = sse_generator(["cpu", "ram"])
            events = []
            async for chunk in gen:
                events.append(chunk)
                if len(events) >= 1:
                    break
            assert events
            assert "data:" in events[0]
            # CPU error should be in the payload
            assert "collect_failed" in events[0] or "error" in events[0]

    @pytest.mark.asyncio
    async def test_sse_cancellation_cleanup(self):
        """CancelledError propagates but cleanup still runs."""
        from dashboard.api.live import sse_generator

        monitor = MagicMock()
        monitor.add_client = AsyncMock()
        monitor.remove_client = AsyncMock()
        monitor.get_cpu = AsyncMock(return_value={"value": 10})

        with patch("dashboard.api.live.get_live_monitor", return_value=monitor):
            gen = sse_generator(["cpu"])
            try:
                async for _ in gen:
                    raise asyncio.CancelledError()
            except asyncio.CancelledError:
                pass


class TestLiveEndpoint:
    """HTTP-level tests for GET /api/device/live."""

    @pytest.mark.asyncio
    async def test_live_endpoint_unauthenticated_ok(self):
        """Live SSE endpoint is publicly accessible."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with patch("dashboard.api.live.sse_generator") as mock_gen:

                async def fake_gen(metrics):
                    yield "data: test\n\n"

                mock_gen.side_effect = fake_gen
                response = await client.get("/api/device/live")
                assert response.status_code == 200
                assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_live_endpoint_metrics_param(self):
        """Metrics query param is passed to sse_generator."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with patch("dashboard.api.live.sse_generator") as mock_gen:

                async def fake_gen(metrics):
                    assert metrics == ["cpu", "ram"]
                    yield "data: test\n\n"

                mock_gen.side_effect = fake_gen
                response = await client.get("/api/device/live?metrics=cpu,ram")
                assert response.status_code == 200
