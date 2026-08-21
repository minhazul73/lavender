"""
SSE endpoint for live monitoring data.
GET /api/device/live → SSE stream of per-metric updates.
Clients subscribe to specific metrics via query params:
  ?metrics=cpu,ram,thermal,battery,network
"""

import asyncio
import json

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from dashboard.services.live import get_live_monitor


router = APIRouter()


async def sse_generator(metrics: list[str]):
    """Generate SSE events pulling from the live monitor buffers.

    Each event is a JSON object:
        {"metric": "cpu", "data": {...}}
    """
    monitor = get_live_monitor()
    allowed = {"cpu", "ram", "thermal", "battery", "network"}
    requested = [m for m in metrics if m in allowed] if metrics else list(allowed)

    try:
        while True:
            # Pull current values from each requested metric
            for metric in requested:
                if metric == "cpu":
                    data = await monitor.get_cpu()
                elif metric == "ram":
                    data = await monitor.get_ram()
                elif metric == "thermal":
                    data = await monitor.get_thermal()
                elif metric == "battery":
                    data = await monitor.get_battery()
                elif metric == "network":
                    data = await monitor.get_network()
                else:
                    continue
                payload = json.dumps({"metric": metric, "data": data}, separators=(",", ":"))
                yield f"data: {payload}\n\n"
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


@router.get("/device/live")
async def live_sse(
    metrics: list[str] | None = Query(None, description="Comma-separated metric names"),
):
    """SSE endpoint streaming live metrics.

    Open with:  EventSource('/api/device/live?metrics=cpu,ram,thermal,battery,network')
    """
    if metrics is not None:
        # Query param may be sent as "metrics=cpu,ram" — split on comma
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