"""
SSE endpoint for live monitoring data.
GET /api/device/live → SSE stream of per-metric updates.
Clients subscribe to specific metrics via query params:
  ?metrics=cpu,ram,thermal,battery,network
"""

import asyncio
import json
from typing import AsyncGenerator, Set

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from dashboard.services.live import get_live_monitor

router = APIRouter()


def make_subscriber(metric, queue):
    """Create a callback that pushes updates into the SSE queue."""
    def callback(value):
        try:
            payload = json.dumps({"metric": metric, "data": value})
            queue.put_nowait("data: " + payload + "\n\n")
        except asyncio.QueueFull:
            pass
    return callback


@router.get("/device/live")
async def live_sse(
    request: Request,
    metrics: str = Query(
        default="cpu,ram,thermal,battery,network",
        description="Comma-separated list of metrics to subscribe to",
    ),
):
    """
    Server-Sent Events stream for live monitoring data.

    Clients connect once and receive pushes as data changes.
    Each metric has its own collection interval (see config.py).

    Query params:
        metrics: comma-separated list of metrics (cpu, ram, thermal, battery, network)
    """
    metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
    metric_set = set(metric_list)

    # Create a queue per connection — subscribers push into it
    queue = asyncio.Queue(maxsize=100)

    # Subscribe to each metric, pushing into the queue
    monitor = get_live_monitor()
    for metric in metric_set:
        if metric in ("cpu", "ram", "thermal", "battery", "network"):
            monitor.subscribe(metric, make_subscriber(metric, queue))

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            for metric in metric_set:
                monitor.unsubscribe(metric, make_subscriber(metric, queue))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
