"""
SSE endpoint for live monitoring data.
GET /api/device/live → SSE stream of per-metric updates.
Clients subscribe to specific metrics via query params:
  ?metrics=cpu,ram,thermal,battery,network
"""

import asyncio
import json
import logging

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from dashboard.services.live import get_live_monitor


logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_METRICS = ("cpu", "ram", "thermal", "battery", "network")


async def sse_generator(metrics: list[str] | None):
    """Generate SSE events pulling from the live monitor buffers.

    The SSE generator itself reads fresh metric values via the live monitor
    getter methods (which do real-time sysfs reads). The background collector
    threads also run independently to populate ring buffers for sparkline history.
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

    # Start background collectors on first SSE client
    await monitor.add_client()
    try:
        while True:
            for metric in requested:
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
                yield f"data: {payload}\n\n"
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        raise
    finally:
        await monitor.remove_client()


from dashboard.auth.deps import get_current_session
from dashboard.auth.session import UserSession
from fastapi import HTTPException, Depends


@router.get("/device/live")
async def live_sse(
    metrics: list[str] | None = Query(None, description="Comma-separated metric names"),
    session: UserSession | None = Depends(get_current_session),
):
    """SSE endpoint streaming live metrics. Requires authenticated session.

    Open with:  EventSource('/api/device/live?metrics=cpu,ram,thermal,battery,network')
    """
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required")

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