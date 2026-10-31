# `dashboard/services/systemd.py` — journal log parsing

**Purpose:** `systemctl` / `journalctl` wrappers for service listing, status,
and structured JSON log retrieval.

## Key changes

- **Timestamp parsing.** Journal `__REALTIME_TIMESTAMP` /
  `_SOURCE_REALTIME_TIMESTAMP` (microsecond epoch) are converted to ISO 8601
  with magnitude-based unit detection (µs > 1e12, ms > 1e9, else s) instead of
  brittle string slicing; `json` import moved out of the per-line loop; fallback
  to `SYSLOG_TIMESTAMP` when no numeric timestamp exists.
- **Frontend alignment.** Epoch heuristic in `live.js` changed from digit-count
  (13 digits = ms) to magnitude (`n >= 1e12`) so 10-digit millisecond epochs and
  13-digit microsecond epochs both resolve correctly.
- **Service detail inspection.** Status parsing extended to unit-file state,
  CPU time, docs links; log entries truncated to 200 chars with severity
  derived from syslog priority.

## Performance improvements

- Log endpoint returns correctly-formatted timestamps without a second pass /
  client-side guessing; per-line overhead reduced (no repeated import, no regex
  string-slicing failures).

## Usage

```python
from dashboard.services.systemd import get_recent_logs

entries = get_recent_logs(lines=20)
# each entry: {"ts": "2026-10-31T18:04:02.123456", "severity": "info",
#              "message": "..."}
```

Exposed via `GET /api/system/logs`.

## Caveats

- Magnitude-based unit detection is a heuristic: a **13-digit millisecond**
  epoch (i.e. year > 5138 in ms) would be misread as microseconds. Not a
  practical concern today, but the unit is not carried in the journal record.
- Log messages are **truncated to 200 chars** per entry by design; do not rely
  on this endpoint for full log content (use `journalctl` directly).
- `systemctl` / `journalctl` invocations still shell out per request; only the
  per-line parsing was optimized.

## Code references

- `dashboard/services/systemd.py:295` — `get_recent_logs()`
- `dashboard/static/live.js` — epoch heuristic (legacy UI)

## Tests

- `tests/unit/test_systemd_logs.py`
- `tests/test_api.py` (`test_system_logs_api`)

## Benchmarks

None recorded. See the parent doc
[`docs/optimized-modules.md`](../optimized-modules.md#verification) for how to
produce real numbers.
