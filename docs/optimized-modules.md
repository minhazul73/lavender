# Optimized Modules — Lavender

Inventory of modules that received explicit performance / resource optimizations in
the lavender codebase. For each: purpose, key changes, performance improvement,
code references, and benchmarks.

**Note on benchmarks:** the repository has no formal benchmark harness (no
`benchmark/`, no `time.perf_counter`-based test fixtures, no recorded latency
numbers). All performance claims below are qualitative, derived from the change
itself and the commit messages. See "Verification" at the bottom for how to
produce numbers if needed later.

Last updated: 2026-10-31 (task t_1495ef63)

---

## 1. `dashboard/services/live.py` — SSE metric collectors

**Purpose:** Real-time metric collection for the SSE stream
(`/api/device/live`). Five per-metric `MetricCollector` subclasses (CPU, RAM,
thermal, battery, network rate), each an independent asyncio task with its own
polling interval and rolling history buffer for sparklines.

**Key changes (chronological):**
- `375fdcb` — "Add SSE live monitoring engine with per-metric collectors".
  Collectors use sysfs / `/proc` reads directly — no subprocess spawning per
  sample. Lazy start: collectors start only when the first SSE client connects
  and stop when the last disconnects.
- `433156f` — "cache UPower probe results in battery collector".
  `BatteryCollector` now memoizes both the UPower availability probe
  (`_upower_checked` flag, ran `upower --version` every cycle before) and the
  device-path lookup (`upower -e`, now cached including a negative result —
  `_upower_device = ""` on failure so a dead UPower is probed once, not every
  3 s).
- `159da0a` / `a957121` / `08fedd0` — "prioritize physical and wifi network
  interfaces over virtual or VPN connections" (and the later `server/` mirror).
  `NetworkRateCollector._primary_interface` replaced a naive
  "first interface with non-zero RX" pick with a multi-factor ranking:
  interface category priority (WiFi > Ethernet > USB > Cellular > other
  physical > VPN/overlay), operstate from `/sys/class/net/<if>/operstate`,
  default-route detection from `/proc/net/route`, and total traffic volume.
  Exclusion list extended with `dummy`.
- `6453905` (docs) — documents `__slots__` on all collectors (memory-efficient
  instances) and `CollectorStats` health tracking (`sample_count`,
  `errors_in_row`, `last_error`).

**Performance improvements:**
- Zero subprocesses in the hot path for CPU/thermal/RAM/network metrics —
  pure `/proc` + sysfs file reads at 1–5 s cadence.
- UPower shell-outs reduced from every battery cycle to at most one per
  collector lifetime (positive or negative result cached).
- `RingBuffer` (`collections.deque(maxlen=...)`) gives O(1) append and bounded
  memory (20–30 datapoints per metric) with no locking for reads.
- `__slots__` on collector classes cuts per-instance memory.
- Collectors idle entirely with no SSE clients (no background CPU when
  nobody is watching).

**Code references:**
- `dashboard/services/live.py:82` — `RingBuffer`
- `dashboard/services/live.py:120` — `CollectorStats`
- `dashboard/services/live.py:128` — `MetricCollector` base
- `dashboard/services/live.py:1062` — `NetworkRateCollector`
- Tests: `tests/unit/test_live_api.py`, `tests/unit/test_live_services.py`,
  `tests/unit/test_network_services.py`, `tests/test_services.py`

**Benchmarks:** none recorded.

---

## 2. `dashboard/services/packages.py` — package manager adapters

**Purpose:** Distro-agnostic package management (apk / apt / pacman / dnf) —
installed list, upgradable list, search, info, install, remove, upgrade.

**Key changes:**
- In-memory 60-second TTL cache (`_PACKAGES_CACHE`, dict with
  `installed` / `timestamp` / `ttl`) for the installed-package listing.
  `get_installed_packages()` returns the cache when fresh;
  `invalidate_packages_cache()` clears it after any install/remove/upgrade so
  mutations never serve stale data.
- `86da32c` — "increase package operation timeouts": install/remove/upgrade now
  pass `timeout=600` to `run_sudo_async` (was default 30 s), and apt runs with
  unattended options configured so large upgrades no longer time out mid-run.

**Performance improvements:**
- One `apk`/`dpkg-query`/`pacman`/`rpm` enumeration per 60 s instead of one per
  page load / API hit — the docstring states the goal explicitly: "reduce host
  CPU and disk I/O load" (matters on the RN7, where enumerating ~1000+
  packages is expensive).
- 600 s timeouts remove false timeouts on slow network package operations
  (reliability rather than raw speed).

**Code references:**
- `dashboard/services/packages.py:15` — `_PACKAGES_CACHE`
- `dashboard/services/packages.py:22` — `invalidate_packages_cache()`
- `dashboard/services/packages.py:624-631` — TTL check + store
- Tests: `tests/unit/test_packages/test_cache_and_wrappers.py`

**Benchmarks:** none recorded.

---

## 3. `dashboard/services/device_info.py` — hardware/OS discovery

**Purpose:** Detects device model, OS distro, kernel, arch, hostname via a
6-level fallback chain (devicetree → `/etc/deviceinfo` → DMI → `hostnamectl`
→ `/etc/machine-info` → `socket.gethostname()`).

**Key changes:**
- `19fbd66` — "add dynamic device info service".
- Result is memoized with `@lru_cache(maxsize=1)` at
  `dashboard/services/device_info.py:156` because hardware and OS identity do
  not change at runtime.

**Performance improvements:**
- The full probe chain (several file reads + up to a `hostnamectl` subprocess)
  runs exactly once per process lifetime; every subsequent
  `GET /api/device/info` returns from memory.

**Code references:**
- `dashboard/services/device_info.py:156` — `@lru_cache(maxsize=1)`
- Tests: `tests/unit/test_device_info_services.py`

**Benchmarks:** none recorded.

---

## 4. `dashboard/services/systemd.py` — journal log parsing

**Purpose:** `systemctl` / `journalctl` wrappers for service listing, status,
and structured JSON log retrieval.

**Key changes:**
- `2891ee6` / `708867a` — "improve system log timestamp parsing". Journal
  `__REALTIME_TIMESTAMP` / `_SOURCE_REALTIME_TIMESTAMP` (microsecond epoch)
  are converted to ISO 8601 with magnitude-based unit detection (µs > 1e12,
  ms > 1e9, else s) instead of brittle string slicing; `json` import moved out
  of the per-line loop; fallback to `SYSLOG_TIMESTAMP` when no numeric
  timestamp exists.
- `861f1b5` — matching frontend fix: epoch heuristic in `live.js` changed from
  digit-count (13 digits = ms) to magnitude (`n >= 1e12`) so 10-digit
  millisecond epochs and 13-digit microsecond epochs both resolve correctly.
- `4152294` — service detail inspection: status parsing extended to unit-file
  state, CPU time, docs links; log entries truncated to 200 chars with
  severity derived from syslog priority.

**Performance improvements:**
- Log endpoint returns correctly-formatted timestamps without a second pass /
  client-side guessing; per-line overhead reduced (no repeated import, no
  regex string-slicing failures).

**Code references:**
- `dashboard/services/systemd.py:295` — `get_recent_logs()`
- `dashboard/static/live.js` — epoch heuristic (legacy UI)
- Tests: `tests/unit/test_systemd_logs.py`, `tests/test_api.py`
  (`test_system_logs_api`)

**Benchmarks:** none recorded.

---

## 5. `dashboard/services/processes.py` — process monitor

**Purpose:** Process listing (procps + BusyBox `ps` formats), load averages,
kill-by-PID.

**Key changes:**
- `ad1b1c8` — "dynamically compute RSS memory from system page size". RSS/VSZ
  for BusyBox processes are read from `/proc/<pid>/stat` and multiplied by the
  actual system page size instead of assuming 4 KiB — correct memory figures
  on any PAGE_SIZE.
- `f7ede1f` — load-average dict expanded with alias keys (`1m`/`5m`/`15m`,
  `load1`/`load5`/`load15`) so frontend consumers need no key-mapping.
- BusyBox 4-column `ps aux` fallback with per-PID `/proc/<pid>/stat`
  inspection for RSS/VSZ/memory %.

**Performance improvements:**
- Single `ps` invocation per request; per-process stat reads only happen for
  the BusyBox fallback path. Alias keys remove repeated key-lookup fallbacks
  on the client side.

**Code references:**
- `dashboard/services/processes.py:148` — `get_system_load()`
- Tests: `tests/unit/test_processes.py`

**Benchmarks:** none recorded.

---

## 6. `dashboard/api/live.py` + `dashboard/static/live.js` — SSE transport

**Purpose:** Server-Sent Events endpoint (`GET /api/device/live?metrics=...`)
and the browser EventSource client.

**Key changes:**
- `375fdcb` — SSE engine: each metric pushed on its own interval (CPU 1 s,
  RAM 3 s, thermal 5 s, battery 3 s, network 2 s) via `StreamingResponse`.
  SSE chosen over WebSocket to keep the stack light.
- `27e17ca` — "optimize SSE hook with onMetric callback and update
  OverviewPage sparkline buffering": the client dispatches each event through
  a per-metric callback instead of a generic handler with metric sniffing, and
  sparkline buffer growth is bounded client-side.
- Failure events are structured: `{"metric": "...", "error": "collect_failed"}`
  (no `data`), so the client never renders partial state.

**Performance improvements:**
- No polling: one persistent connection instead of N HTTP round-trips per
  metric per interval. Per-metric intervals mean slow-changing metrics
  (thermal, 5 s) don't share CPU's 1 s cadence.
- Client-side: per-metric callback avoids parsing/re-dispatching every event
  through every widget; bounded buffers prevent unbounded memory growth on
  long-open tabs.

**Code references:**
- `dashboard/api/live.py` — SSE endpoint
- `dashboard/static/live.js` — EventSource client
- `dashboard/config.py` — `SSE_*_INTERVAL_MS` / `SSE_*_BUFFER`
- Tests: `tests/unit/test_live_api.py`, `tests/unit/test_services.py`

**Benchmarks:** none recorded.

---

## 7. `dashboard/main.py` — static asset caching

**Purpose:** FastAPI app entrypoint, middleware, static file serving.

**Key changes:**
- `8fc51d8` — cache-busting: git hash injected into static asset URLs
  (`/static/...?v=<githash>`) so new deploys are picked up without users
  holding stale CSS/JS.
- `345ee60` — `Cache-Control: no-cache` middleware on static files to prevent
  stale caches at the browser level.

**Performance improvements:**
- Correct cache semantics: browsers revalidate instead of silently serving
  stale bundles (fixes "UI looks broken after deploy" class of bugs; not a
  raw-speed change).

**Code references:**
- `dashboard/main.py` — asset hash injection + `no-cache` middleware

**Benchmarks:** none recorded.

---

## 8. `dashboard/templates/battery.html` — combined fetch (legacy Jinja UI)

**Purpose:** Battery/thermal/CPU-frequency page (now redirects to Overview).

**Key changes:**
- `21da280` — "single combined fetch for all 3 tabs". All three tabs hit
  `/api/device/battery` separately on every tab switch; now one shared
  `loadDeviceInfo()` call stores the result in `_deviceData` and all tabs /
  refresh buttons reuse the cache. Duplicate `loadThermal()` / `loadCpu()`
  definitions deleted.

**Performance improvements:**
- 3 fetches per page load → 1; 1 fetch per tab switch → 0 (cache hit).
- Also deleted 895 lines of stale research docs (`DASHDOT_STUDY.md` etc.).

**Code references:**
- `dashboard/templates/battery.html` (template since removed in React cutover;
  change preserved in git history at `21da280`)

**Benchmarks:** none recorded.

---

## 9. `dashboard/auth/bridge.py` — async subprocess execution

**Purpose:** Native Linux credential verification (shadow → PAM → sudo → doas)
and the async command-execution engine used across all privileged endpoints.

**Key changes:**
- `86da32c` — "improve command execution timeout handling":
  `run_command_async` / `run_sudo_async` / `run_user_service_async` now
  catch both `asyncio.TimeoutError` and builtin `TimeoutError`, and on timeout
  or any exception they `proc.kill()` **and** `await proc.wait()` — previously
  a timed-out child was killed without reaping, leaking zombie processes on
  repeated timeouts.
- `4e740ec` — switched to builtin `TimeoutError` (3.11+ alias of
  `asyncio.TimeoutExpired`) to avoid import-ordering issues.

**Performance improvements:**
- No process leak under timeout conditions (zombies accumulate otherwise and
  consume PIDs/memory over long uptime — critical for an always-on dashboard
  on a phone).

**Code references:**
- `dashboard/auth/bridge.py:146-205` — async runners
- Tests: `tests/unit/test_auth_deps.py`, `tests/test_auth.py`

**Benchmarks:** none recorded.

---

## 10. Frontend cutover: React SPA (`frontend/`, Phase 3–4)

**Purpose:** Replaced the Jinja2 + vanilla-JS UI with a Vite + React + TS SPA
to make the dashboard maintainable.

**Key changes:**
- `6e12b44` — scaffold (Vite + React + TS, auth, theme, test suite).
- `7774fe2` — Phase 3: all dashboard pages migrated.
- `e1414cf` — Phase 4 cutover: Jinja2 removed, SPA served by the FastAPI
  backend.
- `27e17ca` — SSE hook optimization (see §6).

**Performance / resource improvements:**
- Bundled, minified assets served from one build (vs many hand-maintained
  templates + 3 global JS/CSS files); dev builds cached by Vite.
- Per-page component split means a page change rebuilds/loads only its chunk.

**Code references:**
- `frontend/src/` — SPA source; `frontend/src/hooks/useSSE.ts` (SSE hook)
- `frontend/src/pages/Overview/OverviewPage.tsx` — sparkline buffering

**Benchmarks:** none recorded.

---

## Non-optimization refactors (for completeness, not counted above)

- `382e3c4` — removed SSH-loopback auth bridge in favor of native PAM
  (security, not perf).
- `9f1d71f` — modal z-index fix (UI correctness).
- `95f0abd` / `3c56919` — pre-commit hooks, black, flake8 (code quality).
- `d45245a` — replaced silent broad exception handlers with explicit logging
  (reliability).
- `1ec5f55` / `31d4080` — package restructure `dashboard/` → `server/` layout
  in some branches (maintainability; note current working tree still has
  `dashboard/` as the canonical path).

---

## Verification (how to produce real benchmarks later)

No benchmark numbers exist yet. If downstream tasks need them:

1. **Collector latency:** wrap one `collect()` call per collector in
   `time.perf_counter()` — e.g. a 100-iteration script reading
   `CPUFreqCollector.collect()` on the RN7; expect µs–low-ms for sysfs/proc
   reads.
2. **Package cache hit vs miss:** time `get_installed_packages()` twice —
   first call shells out (hundreds of ms on apk), second returns from
   `_PACKAGES_CACHE` (~µs).
3. **SSE throughput:** `curl -N /api/device/live?metrics=cpu` and count events
   per second (should be ~1/s for cpu).
4. **Memory:** `ps -o rss= -p <uvicorn-pid>` with 0 vs 5 SSE clients
   connected — should differ by only a few hundred KB (bounded RingBuffers).

Suggested location for a permanent harness: `tests/benchmarks/` with a
`pytest-benchmark` or plain-perf_counter script gated behind
`make bench` in the Makefile.
