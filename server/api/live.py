"""
SSE endpoint for live monitoring data.
GET /api/device/live → SSE stream of per-metric updates.
Clients subscribe to specific metrics via query params:
  ?metrics=cpu,ram,thermal,battery,network
"""

import asyncio
import json
import logging
import time

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from server.core.config import (
    SSE_BATTERY_INTERVAL_MS,
    SSE_CPU_INTERVAL_MS,
    SSE_NETWORK_INTERVAL_MS,
    SSE_RAM_INTERVAL_MS,
    SSE_THERMAL_INTERVAL_MS,
)
from server.services.live import get_live_monitor


logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_METRICS = ("cpu", "ram", "thermal", "battery", "network")

METRIC_INTERVALS = {
    "cpu": SSE_CPU_INTERVAL_MS / 1000.0,
    "ram": SSE_RAM_INTERVAL_MS / 1000.0,
    "thermal": SSE_THERMAL_INTERVAL_MS / 1000.0,
    "battery": SSE_BATTERY_INTERVAL_MS / 1000.0,
    "network": SSE_NETWORK_INTERVAL_MS / 1000.0,
}


async def sse_generator(metrics: list[str] | None):
    """Generate SSE events pulling from the live monitor buffers.

    Each metric is streamed on its own individually configured interval
    (CPU: 1s, Network: 2s, RAM: 3s, Battery: 3s, Thermal: 5s).
    On client connection, an initial sample of all requested metrics is yielded
    immediately so the client displays live data without initial delay.
    """
    monitor = get_live_monitor()
    if metrics:
        requested = [m for m in ALLOWED_METRICS if m in set(metrics)]
    else:
        requested = list(ALLOWED_METRICS)

    getters = {
        "cpu": monitor.get_cpu,
        "ram": monitor.get_ram,
        "thermal": monitor.get_thermal,
        "battery": monitor.get_battery,
        "network": monitor.get_network,
    }

    async def _emit_metric(metric: str) -> str:
        try:
            data = await getters[metric]()
        except Exception:
            # One bad sensor read must not kill the whole stream, but
            # it should still be visible in the logs and to the client.
            logger.exception("SSE collector failed for metric %r", metric)
            payload = json.dumps(
                {"metric": metric, "error": "collect_failed"},
                separators=(",", ":"),
            )
        else:
            payload = json.dumps(
                {"metric": metric, "data": data}, separators=(",", ":")
            )
        return f"data: {payload}\n\n"

    # Start background collectors on first SSE client
    await monitor.add_client()
    try:
        # Initial burst: emit current state for all requested metrics immediately
        for metric in requested:
            yield await _emit_metric(metric)

        now = time.monotonic()
        next_send = {
            metric: now + METRIC_INTERVALS.get(metric, 1.0)
            for metric in requested
        }

        while True:
            now = time.monotonic()
            due = [m for m in requested if now >= next_send[m]]
            for metric in due:
                yield await _emit_metric(metric)
                interval = METRIC_INTERVALS.get(metric, 1.0)
                next_send[metric] = max(now + interval, next_send[metric] + interval)

            next_due_time = min(next_send[m] for m in requested)
            sleep_sec = max(0.05, next_due_time - time.monotonic())
            await asyncio.sleep(sleep_sec)
    except asyncio.CancelledError:
        raise
    finally:
        await monitor.remove_client()


from server.auth.deps import get_current_session
from server.auth.session import UserSession
from fastapi import HTTPException, Depends


@router.get("/device/live")
@router.get("/live")
async def live_sse(
    metrics: list[str] | None = Query(None, description="Comma-separated metric names"),
    session: UserSession | None = Depends(get_current_session),
):
    """SSE endpoint streaming live metrics. Publicly accessible for overview homepage.

    Open with:  EventSource('/api/device/live?metrics=cpu,ram,thermal,battery,network')
    """

    if metrics is not None:
        flat_metrics = [m.strip() for metric in metrics for m in str(metric).split(",")]
    else:
        flat_metrics = None

    return StreamingResponse(
        sse_generator(flat_metrics),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )