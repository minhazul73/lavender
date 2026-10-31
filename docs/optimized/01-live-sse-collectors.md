# `dashboard/services/live.py` — SSE metric collectors

**Purpose:** Real-time metric collection for the SSE stream
(`/api/device/live`). Five per-metric `MetricCollector` subclasses (CPU, RAM,
thermal, battery, network rate), each an independent asyncio task with its own
polling interval and rolling history buffer for sparklines.

## Key changes

- **Lazy start / stop.** Collectors start only when the first SSE client connects
  and stop when the last disconnects. No background CPU when nobody is watching.
- **UPower probe caching.** `BatteryCollector` memoizes both the UPower
  availability probe (`_upower_checked` flag) and the device-path lookup
  (`upower -e`, cached including a negative result — `_upower_device = ""` on
  failure so a dead UPower is probed once, not every 3 s).
- **Network interface prioritization.** `NetworkRateCollector._primary_interface`
  replaced a naive "first interface with non-zero RX" pick with a multi-factor
  ranking: interface category priority (WiFi > Ethernet > USB > Cellular > other
  physical > VPN/overlay), operstate from `/sys/class/net/<if>/operstate`,
  default-route detection from `/proc/net/route`, and total traffic volume.
  Exclusion list extended with `dummy`.
- **`__slots__` on all collectors** (memory-efficient instances) plus
  `CollectorStats` health tracking (`sample_count`, `errors_in_row`,
  `last_error`).

## Performance improvements

- Zero subprocesses in the hot path for CPU/thermal/RAM/network metrics — pure
  `/proc` + sysfs file reads at 1–5 s cadence.
- UPower shell-outs reduced from every battery cycle to at most one per
  collector lifetime (positive or negative result cached).
- `RingBuffer` (`collections.deque(maxlen=...)`) gives O(1) append and bounded
  memory (20–30 datapoints per metric) with no locking for reads.
- Collectors idle entirely with no SSE clients.

## Usage

The endpoint is the public surface; individual collectors are internal:

```
GET /api/device/live?metrics=cpu,ram,battery
```

The response is an SSE stream; each event carries `metric`, `data`, and
`ts`. Per-collector health is exposed for monitoring via
`collector.stats()` → `{"sample_count": ..., "errors_in_row": ...,
"last_error": ...}`.

## Caveats

- **RingBuffer reads are lock-free, not atomic.** Safe only because appends
  happen in a single asyncio task per metric (documented in the class
  docstring); adding a second writer would require synchronization.
- **Cached UPower state never re-probes.** If UPower comes up later (e.g.
  package installed post-boot), the battery collector keeps returning
  sysfs-only data until the process restarts.
- **Network primary-interface ranking** can pick a VPN/overlay if it is the
  only interface with traffic; the ranking deprioritizes but does not exclude
  them.

## Code references

- `dashboard/services/live.py:82` — `RingBuffer`
- `dashboard/services/live.py:120` — `CollectorStats`
- `dashboard/services/live.py:128` — `MetricCollector` base
- `dashboard/services/live.py:1115` — `NetworkRateCollector`

## Tests

- `tests/unit/test_live_api.py`
- `tests/unit/test_live_services.py`
- `tests/unit/test_network_services.py`
- `tests/test_services.py`

## Benchmarks

None recorded. See the parent doc
[`docs/optimized-modules.md`](../optimized-modules.md#verification) for how to
produce real numbers.
