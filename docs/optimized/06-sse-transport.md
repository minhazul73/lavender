# `dashboard/api/live.py` + `dashboard/static/live.js` — SSE transport

**Purpose:** Server-Sent Events endpoint (`GET /api/device/live?metrics=...`)
and the browser EventSource client.

## Key changes

- **Per-metric intervals.** Each metric pushed on its own interval (CPU 1 s, RAM
  3 s, thermal 5 s, battery 3 s, network 2 s) via `StreamingResponse`. SSE
  chosen over WebSocket to keep the stack light.
- **`onMetric` callback.** The client dispatches each event through a
  per-metric callback instead of a generic handler with metric sniffing, and
  sparkline buffer growth is bounded client-side.
- **Structured failure events.** `{"metric": "...", "error": "collect_failed"}`
  (no `data`), so the client never renders partial state.

## Performance improvements

- No polling: one persistent connection instead of N HTTP round-trips per
  metric per interval. Per-metric intervals mean slow-changing metrics
  (thermal, 5 s) don't share CPU's 1 s cadence.
- Client-side: per-metric callback avoids parsing/re-dispatching every event
  through every widget; bounded buffers prevent unbounded memory growth on
  long-open tabs.

## Usage

**Backend:**
```python
from dashboard.api.live import get_live_metrics_stream
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/api/device/live")
async def live_metrics_api(metrics: str = "all"):
    return StreamingResponse(get_live_metrics_stream(metrics.split(",")),
                             media_type="text/event-stream")
```

**Frontend (`live.js`):**
```javascript
import { setupSSE } from './live.js';

setupSSE({ metrics: ['cpu', 'ram'],
           onMetric: (metric, data) => {
               // Update UI for specific metric
               if (metric === 'cpu') { /* ... */ }
           }});
```

## Caveats

- **SSE vs. WebSockets:** SSE is simpler for server-to-client push but lacks
  bidirectional communication. For future interactive features (e.g., control),
  a WebSocket endpoint would be required.
- **Client-side buffering.** While the server's `RingBuffer` is bounded,
  client-side memory growth is only bounded if `onMetric` handlers correctly
  manage their own historical data (e.g., sparklines).
- **Graceful degradation.** The structured error events allow clients to
  display per-metric failures without breaking the entire stream.

## Code references

- `dashboard/api/live.py` — SSE endpoint
- `dashboard/static/live.js` — EventSource client
- `dashboard/config.py` — `SSE_*_INTERVAL_MS` / `SSE_*_BUFFER`

## Tests

- `tests/unit/test_live_api.py`
- `tests/unit/test_services.py`

## Benchmarks

None recorded. See the parent doc
[`docs/optimized-modules.md`](../optimized-modules.md#verification) for how to
produce real numbers.
