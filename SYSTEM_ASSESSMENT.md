# System & Software Engineering Assessment — RN7 Linux Dashboard

**Generated:** 2026-08-16  
**Context:** RN7 Linux Dashboard (`/home/rahat/hermes-device-dashboard`)  
**Device:** Redmi Note 7 (lavender), postmarketOS v26.06, aarch64/musl, ~3GB RAM  
**Status:** Backlog — not yet actioned. User intends to tackle improvements in chunks.

---

## Research consumed

5 articles across embedded systems, FastAPI performance, subprocess overhead, and web dashboard optimization:

- **RunTime Recruitment** — embedded firmware under limited resources: modular design, functionality segregation, avoid over-provisioning, test under actual constraints
- **Comarch** — memory optimization in C/embedded: every allocation counts, reduce footprint before scaling up, same functionality with fewer resources
- **KissPeter** — FastAPI performance: 4x throughput gain from proper async, response model simplification, avoiding sync endpoints on the event loop
- **Leapcell** — 10 FastAPI optimization tips: async/await throughout, response_model for serialization control, caching, connection pooling, worker strategy
- **DEV.to (Igor Benav)** — FastAPI mistake: single worker uses one CPU core only; under load, that core becomes the bottleneck
- **ResearchGate** — lazy loading + code splitting: up to 40% page load reduction; defer off-screen content
- **Zigpoll** — interactive dashboard loading: paginate/lazy-load large tables, reduce initial rendering load

Key principles extracted for this project:

1. **Re-execute avoidance** — Every `subprocess.run` / `systemctl` / `upower` call is a fork+exec. On a 3GB phone with CPUQuota=50%, repeated heavy calls in request handlers are the most expensive thing the dashboard does. Cache where data is stable; batch where data is related.
2. **Async correctness** — FastAPI's value is async concurrency. Blocking the event loop with `subprocess.run` in an `async def` endpoint defeats the model. Use `run_in_executor` for CPU/IO-bound shell calls, or keep endpoints lean.
3. **Memory discipline** — MemoryMax=300M, MemoryHigh=200M, current usage ~168MB RSS, peak ~200MB. The service is within budget but has no headroom for spikes. Large payloads, unbounded list returns, and per-request allocations matter.
4. **Payload efficiency** — Every API endpoint returns full objects. Some calls return raw `systemctl status` output as a string field *and* parsed fields. Some calls return 42 full service objects when the overview only needs counts. No selective-field responses.
5. **Startup cost** — Import-time subprocess calls (see below) run on every worker start. With `RestartSec=5` and potential restarts, that's wasted cycles.

---

## What's unoptimized in the current build

### 1. Import-time subprocess calls (definite bug, immediate fix)

`dashboard/dependencies.py`:

- `get_hermes_version()` (line 104) — runs `[HERMES_BIN, "--version"]` via subprocess
- `get_hermes_skills()` (line 112) — does `os.listdir()` on import

These are defined as functions but if any module imports them at module level or calls them outside a request context, the subprocess runs at import time. More critically, the `from dashboard.dependencies import ...` pattern in every service module means these modules are loaded at startup. If anything triggers `get_hermes_version()` during import/startup, that's a wasted subprocess on every restart.

**Impact:** low–medium. Not currently triggered at import (they're called per-request), but the pattern is fragile — a future edit could easily trigger import-time execution.

### 2. No caching anywhere (every request re-runs everything)

Every endpoint calls its service function fresh. No caching, no TTL, no conditional re-fetch.

Specific high-cost examples:

- `/api/device/battery` (line 63–71 of `device.py`) calls **four separate functions** that each do work: `get_battery_info()` (upower -e + upower -i = 2 subprocess calls), `get_thermal_zones()` (reads 12+ files from /sys), `get_cpu_frequencies()` (reads N cpu/*/cpufreq files), `get_cpu_scaling_available()` (reads cpu0 cpufreq files). **One API call = 2 subprocesses + 12+ file reads + N file reads.** And it's called from the overview page on every load.
- `/api/system/services` (line 31–39 of `system.py`) runs `systemctl --user list-units` + `systemctl list-units` (2 subprocesses, 15s timeout each) on every request. The overview page calls this to render "27 active of 42 total".
- `/api/system/memory` calls both `get_memory_info()` (reads /proc/meminfo) and `get_memory_human()` (runs `free -h` subprocess) — two ways to get the same data.
- `/api/hermes/network-quality` (line 83–86 of `hermes.py`) calls `get_network_quality()` which runs **two ping subprocesses** (gateway + 8.8.8.8) on every request.
- `/api/system/storage` calls `get_disk_usage()` (df -h subprocess) + `get_mounts()` (reads /proc/mounts) + `get_dir_usage()` (up to 4 `du -sh` subprocesses, 30s timeout each).

**Impact:** high. This is the single biggest resource waste in the project. A user refreshing the overview page triggers ~10 subprocess calls and 12+ file reads. On a phone with 50% CPU quota, this adds up fast.

**What data is actually stable?**

| Data | How often it changes | Cache TTL suggestion |
|---|---|---|
| Thermal zones (names, types) | Never (hardware) | Cache forever |
| CPU freq governors, min/max | Rarely (reboot/config change) | Cache 5–10 min |
| DNS servers (/etc/resolv.conf) | Rarely | Cache 5 min |
| Installed packages count | On apk upgrade only | Cache 10 min |
| Upgradable packages | On apk upgrade only | Cache 10 min |
| Users/groups (/etc/passwd, /etc/group) | On useradd/change | Cache 5 min |
| Services list | On service start/stop/enable | Cache 30–60s |
| Battery %/state | Seconds (charging/discharging) | Don't cache, or 5–10s max |
| Memory usage | Seconds | Don't cache, or 10–15s |
| Network interfaces | On hotplug/reconfigure | Cache 30s |
| Thermal temps | Seconds | Don't cache, or 10s |
| CPU freqs | Milliseconds (dynamic Scaling) | Don't cache, or 5s |

### 3. API endpoints return too much data

Every endpoint returns the full service object. Examples:

- `/api/system/services` returns all fields for all 42 services: name, load_state, active_state, sub_state, scope. That's fine for the services page, but the overview only needs `count` and `active_count`. The API doesn't have a lightweight path.
- `/api/device/battery` returns the full battery object (20+ fields), full thermal array (12 zones × 4 fields), full cpu_freq array (4+ CPUs × 3 fields), and cpu_scaling. The overview page uses maybe 3 fields from this payload.
- `/api/hermes/status` returns gateway + dashboard status objects that include the full `systemctl status` output as a string field (`output`) plus parsed fields. That raw output string is large and not used by the overview.
- `/api/system/storage` returns disks + mounts + dir_usage. The overview only needs the root disk entry.

**Impact:** medium–high. Larger JSON payloads = more serialization time, more network transfer, more client-side parsing. On a phone, this is measurable.

### 4. Blocking the async event loop with subprocess calls

All service functions use `subprocess.run` (blocking). All endpoint handlers are `async def` but call these blocking functions directly — no `run_in_executor`. In a single-worker uvicorn, this means one request blocks the entire event loop during the subprocess call.

**Impact:** medium. With one worker and 50% CPU quota, a slow endpoint (e.g. `/api/system/storage` with 4 `du -sh` calls at 30s each = up to 120s of blocking) would stall everything. Currently no concurrent requests happen because it's a single-user dashboard, but the pattern is wrong and would break under any concurrency.

**The right pattern:** wrap blocking calls in `run_in_executor` (thread pool) or use `asyncio.create_subprocess_exec` for true async subprocess. For a low-traffic dashboard, thread pool is simpler and correct.

### 5. Multiple subprocess calls where one would do

- `get_memory_info()` reads /proc/meminfo (file read). `get_memory_human()` runs `free -h` (subprocess). Both return memory data. The endpoint calls both.
- `get_battery_info()` runs `upower -e` (find battery) then `upower -i <path>` (get info). Two subprocess calls. Could be one if the path is known (it is — `/org/freedesktop/UPower/devices/battery_qcom_battery` on this device).
- `get_thermal_zones()` reads /sys/class/thermal/thermal_zone*/type and temp as separate open() calls per zone. For 12 zones, that's 24+ file opens. Could batch-read with os.scandir or read multiple files in one pass.

**Impact:** low–medium. Each avoided subprocess is a fork+exec saved.

### 6. Storage `get_dir_usage()` — 4 `du -sh` calls, 30s timeout each, no depth limit

`storage.py` line 90–114: calls `du -sh` on `/`, `/home`, `/var`, `/tmp` sequentially. Each call has a 30s timeout and can descend deep into large directories. On a phone, `du -sh /` can take a long time and consume I/O.

The overview doesn't even use this data — only the (now-deleted) storage page did. This function is still called by the API even though the storage page is gone.

**Impact:** medium–high. This is the most expensive single API call. If the overview or any page calls `/api/system/storage`, it triggers up to 4 `du -sh` subprocesses. Currently the overview stores only `get_disk_usage()` (df -h), not dir_usage, so this is dead weight in the API.

### 7. `/api/hermes/network-quality` runs 2 pings on every overview load

The overview page fetches `/api/hermes/network-quality` which calls `get_network_quality()` — this runs ping to gateway + ping to 8.8.8.8. Two ICMP subprocess calls, each up to 10+ seconds. On every page load.

**Impact:** medium. Ping is cheap individually but doing it on every overview refresh is wasteful. Network quality doesn't change every 30 seconds.

### 8. CPUQuota=50% means half the phone's CPU is unavailable to the dashboard

`systemd` service unit sets `CPUQuota=50%`. On a 4-core phone, that's 2 cores worth of time. On a 2-core phone, that's 1 core. The dashboard can never use more than half the CPU.

Combined with the blocking-subprocess pattern, a single slow endpoint could saturate the allowed CPU and stall the event loop.

**Impact:** structural. The dashboard is already constrained to half the phone's CPU. Everything else compounds on top of that.

### 9. Memory headroom is thin

Current RSS: ~168MB. Peak: ~200MB. Limit: 300MB (hard), 200MB (high/throttle). The service is running right at the High threshold. Any payload spike, large JSON serialization, or memory leak would hit the 300M hard limit and get OOM-killed by systemd.

The current memory usage is fine for the current workload, but there's no margin for the "more data on overview" improvements from the UI assessment — those would increase payload sizes and per-request allocations.

**Impact:** medium. The UI improvements (more data per card) will increase memory pressure. Need to be mindful of payload size and avoid unbounded lists.

### 10. No selective field responses (no `?fields=` or lightweight endpoints)

Every endpoint returns the same full object regardless of who calls it. The overview page (lightweight, 6 cards) gets the same payload shape as the detail pages (full tables). There's no way for a client to request only what it needs.

**Impact:** medium. A lightweight `/api/system/services/count` endpoint would serve the overview without parsing 42 full service objects. A `/api/device/battery/overview` endpoint would return only the 4–5 fields the overview card needs.

### 11. Per-request parsing of large text outputs

- `get_service_status()` parses the full `systemctl status` output line-by-line with regex, extracting name, active, PID, memory, CPU. But it also stores the entire raw `output` string in the response. That raw output is ~1–2KB per service and is unused by the overview.
- `get_gateway_status()` and `get_dashboard_status()` do the same — full raw output stored in response.

**Impact:** low–medium. Wasted memory on large string fields that no template uses.

### 12. Hermes session/connection data from SQLite reads on every request

`dashboard/hermes/gateway.py` line 101+ reads `HERMES_STATE_DB` (SQLite) on every `/api/hermes/sessions` and `/api/hermes/memory-pressure` call. Opening a SQLite connection, querying, closing — per request. Could be cached or connection-pooled.

**Impact:** low. SQLite is fast, but per-request open/close adds up over many refreshes.

### 13. Packages endpoint runs `apk info` and `apk list --upgradable` on every request

`get_installed_count()` runs `apk info` (subprocess, 15s timeout) on every `/api/device/packages` call. `get_upgradable_packages()` runs `apk list --upgradable` (subprocess, 15s timeout). Both are stable data that changes only on `apk upgrade`.

**Impact:** medium. Two subprocess calls per packages page load. Cacheable for 10 minutes.

### 14. UI-side: 6 independent fetch() calls on overview page load

`index.html` lines 74–184: six separate `fetch()` calls firing on `DOMContentLoaded`, each independently calling a different API endpoint. All six run in parallel (good — that's how fetch works), but:

- They all have independent `.catch()` handlers that set "Failed to load" — no unified loading state
- They all independently render into their card — no coordination
- There's no loading indicator on the overview itself (each card shows its own "Loading..." placeholder until its specific fetch completes)
- If one fails, the others still render — inconsistent state

**Impact:** low (client-side only, doesn't affect server resources). But the UX is: page loads, shows 6 "Loading..." placeholders, then they populate one by one as the fetches complete. No unified loading/ready state.

### 15. Startup verification — the service's own health check calls its own API

The `hermes-device-dashboard.service` unit has `After=hermes-gateway.service` but no health-check logic. If the dashboard crashes, it restarts after 5s. There's no startup verification that the API is actually serving. The `create_start_app_handler` (line 131–135 of `main.py`) is a no-op.

**Impact:** low. Not a resource issue, but a reliability gap — a broken startup would silently restart in a loop.

---

## What's already optimized well

- **Service layer separation** — each concern (systemd, battery, storage, network, processes, packages, users, power, hermes) is its own module. Clean architecture, easy to optimize individually.
- **Config-driven thresholds** — thermal warn, memory pressure, log lines, top processes, top dirs all in `config.py`. Easy to tune without code changes.
- **Pseudo-FS filtering** — storage.py correctly filters tmpfs/devtmpfs/proc/sysfs etc. from df output. Good.
- **Bind-mount dedup** — storage.py deduplicates by device, keeping shortest mount path. Prevents duplicate entries for /, /home, /var/tmp on the same device.
- **BusyBox ps handling** — processes.py correctly handles 4-column BusyBox ps output, supplements RSS from /proc/PID/stat. Good.
- **ip -o addr parsing** — network.py correctly parses the one-line-per-address format without expecting flags/mtu blocks. Good.
- **upower parsing** — battery.py handles same-line `key: value`, multi-line continuation, known qcom battery path fallback. Good.
- **Security hardening** — systemd unit has NoNewPrivileges, ProtectSystem=strict, ProtectHome=read-only, PrivateTmp, ReadWritePaths scoped to project dir. Good.
- **Resource limits** — MemoryMax=300M, MemoryHigh=200M, CPUQuota=50%. Service is constrained appropriately for a phone.
- **Error handling** — every service function catches exceptions and returns error dicts. No unhandled exceptions propagate to the API layer.
- **Sudo fallback pattern** — systemd.py tries without sudo first, falls back to sudo. Good for user-scope services.

---

## Bottom line

The dashboard's architecture is clean and the service layer is well-structured, but the implementation is **unoptimized in the ways that matter most on a 3GB phone with 50% CPU quota**:

1. **No caching** — every request re-runs every subprocess. This is the biggest waste.
2. **Too many subprocess calls per request** — battery endpoint = 2 upower calls + 12+ file reads + N cpu file reads. Network quality = 2 pings. Storage = 1 df + 4 du. Services = 2 systemctl calls.
3. **Blocking the async event loop** — all subprocess calls are synchronous in async endpoints.
4. **Over-serialization** — endpoints return more data than the overview needs, including raw text strings that no template uses.
5. **No lightweight endpoints** — the overview can't ask for "just the counts" or "just the battery %"; it gets the full objects.

The good news: most of these are independent, chunkable fixes. Caching can be added incrementally (start with the most stable data — thermal zones, DNS, packages, users). Lightweight endpoints can be added alongside existing ones. The blocking-subprocess pattern can be fixed with `run_in_executor` without changing the service layer.

---

## Backlog (chunked — to be tackled incrementally)

_Date each chunk as it's started._

### Chunk backlog (empty — waiting for user direction)

_No chunks assigned yet. User will pick chunks from the unoptimized list above._
