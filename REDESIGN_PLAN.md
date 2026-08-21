# Dashboard Redesign Plan — RN7 Linux Dashboard

**Created:** 2026-08-21  
**Scope:** Reconfigure entire dashboard UI + add SSE live monitoring  
**Constraint:** Must feel light on a ~3GB phone with 50% CPU quota  
**Commit identity:** Minhazul Islam <minhazul73@gmail.com> (already configured)

---

## Principles

1. **Lightweight first** — vanilla JS, no chart libraries, no frameworks, no heavy CSS effects (no backdrop-blur on a phone). SVG sparklines only where needed (inline, no library).
2. **Live overview** — SSE push for CPU freq, RAM, thermal, battery, network rate. Each metric has its own interval. No fetch() bursts.
3. **Battery + network folded into overview** — if the UI is done right, no separate tabs needed for monitoring. Detail pages remain for deep dives (connectivity ping, WiFi info, battery details).
4. **Small commits** — one logical change per commit, reviewable, reversible.
5. **Consistent design language** — every page uses the same card style, same tab style, same status indicators, same color coding per widget.

---

## Phase 1: SSE Engine + Per-Metric Collectors (server-side foundation)

**File:** `dashboard/services/live.py` (new) — per-metric collectors, timers, rolling buffers, lazy start/stop  
**File:** `dashboard/api/live.py` (new) — SSE endpoint `/api/device/live`  
**File:** `dashboard/main.py` — register `/api/device/live` route  
**File:** `dashboard/config.py` — add SSE/poll intervals config

### 1a. SSE endpoint + collector framework
- One SSE endpoint that clients connect to
- Per-metric collectors: each metric gets its own timer, interval, rolling buffer
- Lazy start: collectors start when first client connects, stop when last disconnects
- Push format: SSE message per metric update, tagged by metric name
- Rolling buffer: last N values per metric (for sparklines)

### 1b. CPU freq collector
- Reads `/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq` per core
- Interval: 1s, buffer: 30 samples
- No subprocess, pure sysfs

### 1c. RAM collector
- Reads `/proc/meminfo`
- Interval: 3s, buffer: 20 samples
- Replaces `free -h` subprocess (duplicate data)

### 1d. Thermal collector
- Reads `/sys/class/thermal/thermal_zone*/temp` + `type`
- Interval: 5s, buffer: 20 samples
- Batch-read 12 zones at once

### 1e. Battery collector
- Reuses `get_battery_info()` logic on a timer
- Interval: 3s, buffer: 30 samples of %
- Only overview-needed fields pushed

### 1f. Network rate collector
- Sysfs delta from `/sys/class/net/<iface>/statistics/rx_bytes` + `tx_bytes`
- Interval: 2s, buffer: 30 samples
- **Eliminates 2 ping subprocesses** from every overview load

---

## Phase 2: Redesign Overview as Live Monitoring Hub

**File:** `dashboard/templates/index.html` — complete rewrite  
**File:** `dashboard/static/style.css` — add sparkline CSS, health row, enriched card styles  
**File:** `dashboard/static/script.js` — SSE client + sparkline renderer (shared)

### 2a. Health/status row at top
- 4–6 colored indicators (battery, disk, memory, services, CPU temp, network)
- "Is my device OK?" answer in one glance

### 2b. Overview cards (enriched, live)
- **CPU card:** per-core sparklines + current freq + governor + min/max. Grow: higher.
- **RAM card:** used/total big stat + bar + swap + pressure + sparkline. Grow: high.
- **Battery card (folded in):** % + gauge + temp + voltage + charge rate + state badge + sparkline. Grow: high.
- **Network card (folded in):** up/down rate + sparkline graphs + interface type + speed. Grow: medium.
- **Storage card (enriched):** root disk + small mount table (top 3) + largest dir. Grow: medium.
- **Services card (enriched):** active + failed/inactive counts + "View All →". Grow: medium.
- **Hermes card (enriched):** gateway + dashboard + sessions + memory pressure. Grow: lower.
- **Device info block:** model, vendor, battery tech, CPU arch. Small, static.

### 2c. SSE client in overview JS
- Connect to `/api/device/live`
- Listen for per-metric pushes
- Update only what changed (sparkline extends, gauge slides, numbers tick)
- No fetch() bursts, no "Loading..." after initial connect

### 2d. Sparkline rendering
- Lightweight inline SVG, no library
- Each sparkline = small SVG path from rolling buffer
- CSS-styled (color per widget)

---

## Phase 3: Redesign Remaining Pages (consistent, not heavy)

### 3a. battery.html — simplify to one rich view
- Keep battery + thermal + CPU data, but present as one flowing page, not tab-fragmented
- Or keep tabs but make them consistent with overview design language
- Remove separate page if battery is fully folded into overview — keep only if deep detail needed

### 3b. network.html — one flowing page
- Interfaces + WiFi + DNS + connectivity as continuous sections, not tab-fragmented
- Keep ping as a tool section at bottom

### 3c. services.html — keep, style consistent
- Table stays, but use same card style, same status indicators as overview

### 3d. processes.html — keep, style consistent
- Same card/table style

### 3e. packages.html — keep tabs, style consistent
- Same design language

### 3f. users.html — keep tabs, style consistent

### 3g. power.html — keep, add battery context
- Show current battery % before offering reboot
- Add suspend if available

---

## Phase 4: Cleanup (unblock, improve)

### 4a. Remove `get_dir_usage()` dead weight
- storage.py: remove 4 `du -sh` calls with 30s timeout each
- Never used by any page now

### 4b. Network quality: ping → sysfs delta
- Replace ping-based `/api/hermes/network-quality` with sysfs delta collector
- Two ping subprocesses gone from every overview load

### 4c. Static/dynamic split
- Device info (model, CPU brand, RAM size, storage layout) loaded once at startup
- Not re-read per request

### 4d. Lightweight overview endpoints
- New endpoints that return only what overview needs
- No raw `systemctl` output strings

### 4e. Compression middleware
- Add gzip compression for API responses

### 4f. Remove `free -h` duplicate
- `get_memory_human()` subprocess when `/proc/meminfo` gives same data

### 4g. `run_in_executor` for blocking subprocess calls
- Wrap subprocess calls in thread pool executor in async endpoints

---

## Phase 5: Style Polish (optional, after function)

- Consistent SVG/mini-icon per widget (not emoji mix)
- Per-widget color coding carried through to charts
- Grow-based layout (not uniform grid)
- Sparkline styling per widget color

---

## Commit Order (small commits)

1. Add `dashboard/services/live.py` — collector framework + CPU collector
2. Add `dashboard/api/live.py` — SSE endpoint + register route in main.py
3. Add RAM collector to live.py
4. Add thermal collector to live.py
5. Add battery collector to live.py
6. Add network rate collector to live.py
7. Add SSE client + sparkline renderer to script.js
8. Rewrite index.html — health row + enriched live cards + SSE connect
9. Enrich storage card (mounts + largest dir) on overview
10. Enrich services card (failed/inactive counts) on overview
11. Enrich Hermes card (sessions + memory pressure) on overview
12. Add device info block to overview
13. Remove `get_dir_usage()` dead weight from storage.py
14. Replace ping-based network quality with sysfs delta
15. Static/dynamic split — load stable data once
16. Add compression middleware
17. Remove `free -h` duplicate from memory service
18. `run_in_executor` for blocking subprocess calls
19. Simplify battery.html (one rich view, not tabs)
20. Simplify network.html (one flowing page, not tabs)
21. Style consistency pass — services, processes, packages, users, power pages
22. Power page — add battery context
23. Visual polish — icons, colors, grow layout, sparkline styling
24. Final verification + cleanup

~24 small commits. Each one is self-contained.

---

## What "not heavy" means in practice

- **No chart library** — inline SVG sparklines only, ~50 lines of JS
- **No framework** — vanilla JS, same as now
- **No heavy CSS** — no backdrop-filter blur (expensive on mobile), no animations beyond simple transitions
- **Same card grid** — already there, just enriched
- **Same sidebar** — already there, just maybe reorganized
- **Same dark theme** — already there, just consistent color coding
- **SSE, not WebSocket** — lighter server-side (no socket.io), enough for push
- **Sysfs reads, not subprocess** — CPU, RAM, thermal, network all become file reads instead of fork+exec

---

**Start:** Phase 1, step 1a — `dashboard/services/live.py` + `dashboard/api/live.py` + route registration
