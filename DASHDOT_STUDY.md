# Dashdot Study — Architecture & "How It Feels So Light" Analysis

**Source:** https://github.com/MauriceNino/dashdot  
**Live demo:** https://dash.mauz.dev  
**Studied:** 2026-08-21

---

## What dashdot is

A single-node server monitoring dashboard with glassmorphism UI. Targets small VPS and private servers — the same niche as this RN7 dashboard. Shows OS info, CPU (per-core sparklines + temps), RAM, storage (donut chart + disk list), network (speed graphs + interface info). Live demo runs on a QEMU x64 Debian VM with 12 cores, 31.3GB RAM, 1TB storage.

---

## Tech stack

| Layer | Technology | Version |
|---|---|---|
| Frontend framework | React 19 + React DOM | 19.2.4 |
| UI components | antd (Ant Design) | 5.29.3 |
| Styling | styled-components | 6.1.19 |
| Animations | framer-motion | 12.34.3 |
| Charts | recharts | 3.7.0 |
| Icons | FontAwesome (SVG) + @fortawesome/react-fontawesome | 7.1.0 / 0.2.6 |
| State | store (simple store) + React state | 2.0.12 |
| Real-time transport | socket.io-client | 4.8.3 |
| Build tool | Vite | 7.2.4 |
| Language | TypeScript 5.9.3 | — |
| Backend runtime | Node.js (Express 5.2.1) | — |
| System data | systeminformation 5.31.1 | — |
| Real-time server | socket.io (server) | 4.8.3 |
| Bundler (server) | esbuild | 0.27.3 |
| Mono-repo | Turborepo + yarn workspaces | — |
| Linting | Biome | 2.3.13 |

**Structure:** 3 apps in a monorepo:
- `@dashdot/server` — Express + socket.io server, reads system data, serves the built frontend, pushes updates via WebSocket
- `@dashdot/view` — React SPA built by Vite, connects to server via socket.io-client
- `@dashdot/cli` — CLI tool (separate)

**Deployment:** Docker container with `--privileged` and `-v /:/mnt/host:ro` — reads host's `/proc`, `/sys`, block devices directly from inside the container. Single port (3001).

---

## Architecture — the key design decisions that make it light

### 1. Single process, in-process data collection

The entire dashboard is **one Node.js process**. No separate agents, no database, no external services. The server reads system data directly using `systeminformation` (which wraps `/proc`, `/sys`, `ps`, `df`, etc.) and pushes it to connected clients via WebSocket.

Contrast with the RN7 dashboard: **separate Python service modules** (`systemd.py`, `battery.py`, `storage.py`, `network.py`, `processes.py`, `packages.py`, `users.py`, `power.py`, `hermes/gateway.py`) — 10+ modules, each making independent subprocess calls. More flexible for a multi-feature dashboard, but heavier per-request.

### 2. Background polling with `LazyObservable` — the engine

This is the core of the smoothness. From `dynamic-info.ts`:

```typescript
class LazyObservable<T> implements Subscribable<T> {
  // Creates a ReplaySubject buffer, starts polling only when subscribed,
  // stops polling when no subscribers remain (lazy start/stop).
  // Uses RxJS interval() + mergeMap(dataFactory) for polling.
  // Stores last N datapoints in the buffer (per-widget configurable).
}
```

**What this means:**
- CPU, RAM, network poll every **1000ms** by default (`cpu_poll_interval`, `ram_poll_interval`, `network_poll_interval` all = 1000)
- Storage polls every **60000ms** (`storage_poll_interval` = 60000)
- GPU polls every **1000ms** (when enabled)
- Each widget keeps a rolling buffer of **20 datapoints** (`cpu_shown_datapoints` = 20, same for RAM/network/GPU)
- Polling **starts only when a client connects** (lazy) and **stops when the last client disconnects** — no background collection when no one is viewing
- Each poll calls one `systeminformation` function (e.g. `si.currentLoad()`, `si.mem()`, `si.fsSize()`, `si.blockDevices()`, `si.networkStats()`)

**Why it feels smooth:** The data collection is a steady, predictable heartbeat. No bursty requests. The WebSocket pushes a single update per widget per tick. The frontend receives a stream, not a series of HTTP requests.

### 3. WebSocket push, not HTTP polling

From `index.ts`:

```typescript
io.on('connection', (socket) => {
  subscriptions.push(obs.cpu.subscribe((cpu) => socket.emit('cpu-load', cpu)));
  subscriptions.push(obs.ram.subscribe((ram) => socket.emit('ram-load', ram)));
  subscriptions.push(obs.storage.subscribe(async (storage) => socket.emit('storage-load', storage)));
  subscriptions.push(obs.network.subscribe(async (network) => socket.emit('network-load', network)));
  // ...
});
```

The server **pushes** data to the client. The client doesn't poll. This means:
- No HTTP overhead per update (headers, TCP handshake, etc.)
- Server controls the rate — one message per widget per interval
- Client just renders what it receives

Contrast with the RN7 dashboard: **6 independent `fetch()` calls** on page load, each hitting a different HTTP endpoint, each doing its own subprocess work. Real-time updates require manual re-fetch or HTMX triggers.

### 4. `systeminformation` — one library, many data sources

`systeminformation` (si) is the only data collection library. It wraps:
- `/proc/cpuinfo`, `/proc/loadavg`, `/proc/meminfo`, `/proc/stat`
- `/sys/class/thermal/`, `/sys/devices/system/cpu/`
- `df`, `lsblk`, `mount` equivalents
- `networkInterfaces()`, `networkStats()`

**One npm dependency** handles CPU, RAM, storage, network, GPU, OS, topology, UPTIME, etc. The server doesn't spawn multiple subprocesses — it calls one library function per widget per tick.

Contrast with the RN7 dashboard: each service module spawns its own `subprocess.run()` calls — `systemctl`, `upower`, `df`, `ip`, `ps`, `free`, `apk`, `ping`, `journalctl`, etc. That's 10+ distinct subprocess types, each a fork+exec.

### 5. Network monitoring via `/sys/class/net/<iface>/statistics/` — zero subprocess

From `network.ts`:

```typescript
// Reads rx_bytes and tx_bytes directly from sysfs
const { stdout } = await exec(`cat ${NET_INTERFACE_PATH}/statistics/rx_bytes;` +
                                `cat ${NET_INTERFACE_PATH}/statistics/tx_bytes;`);
// Computes rate as delta / delta-time — no ping, no iptraf, no subprocess per packet
```

This is the lightest possible network monitoring: read two integers from sysfs, compute the delta since last read. No ping subprocesses, no packet capture, no `speedtest` unless explicitly configured.

Contrast with the RN7 dashboard: `ping_test()` spawns a `ping` subprocess with timeout 10+seconds for each gateway + internet check. On every overview load.

### 6. Static vs dynamic split — heavy data loaded once

From `index.ts`:

```typescript
await loadStaticServerInfo();  // OS, arch, CPU model, RAM layout, storage layout, network type — loaded once at startup
const obs = getDynamicServerInfo();  // CPU load, RAM usage, storage usage, network rate — polled
```

Static data (OS name, CPU brand/model/cores, RAM size/type/frequency, storage brand/type/size) is loaded **once** at server startup. Dynamic data (per-core load %, RAM used/available, storage used/total, network up/down rate) is polled.

This matters because static data is cheap to compute once and expensive to recompute. The RN7 dashboard recomputes everything on every request — `get_battery_info()` runs upower every time, `get_thermal_zones()` reads 12+ files every time, `get_cpu_frequencies()` reads N files every time.

### 7. Lazy start/stop — no data collection when idle

The `LazyObservable` starts polling only when the first client subscribes, and stops when the last client disconnects. If no one is viewing the dashboard, **zero data collection happens**. Zero CPU, zero subprocess, zero memory for buffers.

The RN7 dashboard's service layer has no concept of "idle" — every endpoint call triggers fresh subprocess work regardless of whether it's the 1st or 100th refresh.

### 8. Rolling buffer of datapoints — charts come for free

Each widget stores the last N datapoints (20 by default). When a new value arrives via WebSocket, it's pushed to the buffer, the oldest falls off, and recharts re-renders. The charts are always showing the last 20 samples — no history DB, no disk storage, no query.

Contrast with the RN7 dashboard: every page shows point-in-time values. No sparklines, no history. There's no buffer, no chart library, no time-series concept.

### 9. Compression + caching headers

From `index.ts`:

```typescript
app.use(compression());  // gzip/brotli compression
router.use(express.static(..., { maxAge: '1y', setHeaders: ... }));  // 1-year cache for static assets
```

Static assets (JS bundle, CSS, images) are cached for 1 year with hash-based filenames (Vite does this by default). The HTML is cache-busted (`max-age=0`). This means after the first load, subsequent refreshes only download the data via WebSocket — the bundle is already cached.

### 10. Single page, no nav between "pages"

The dashboard is one view. No sidebar navigation between pages. Widgets are laid out in a responsive grid. No route changes, no page reloads, no template rendering per view.

Contrast with the RN7 dashboard: 10 pages (overview, services, processes, storage, network, battery, hermes, packages, users, power), each a separate Jinja2 template, each rendered by FastAPI. Navigating between them is a full page load.

---

## Visual design — what makes it look polished

### Glassmorphism

The signature look: frosted-glass cards with:
- Semi-transparent backgrounds (`rgba` with backdrop blur via CSS `backdrop-filter`)
- Subtle borders
- Soft shadows/layer depth
- Blur effect on the background behind cards

The RN7 dashboard uses flat dark cards (`--bg-card: #1c2128`) with solid borders — no glass effect, no depth.

### Per-widget icon + color coding

Each widget has a colored square icon (blue CPU, green storage, red RAM, yellow network) that serves as both icon and color anchor. The icon color carries through to the charts (CPU sparklines are blue, RAM bar is red/pink, storage donut is green, network graphs are yellow).

The RN7 dashboard uses emoji icons (⚙️, 💾, 🧠, 🌐, 🔋, 🤖) in the sidebar and card headers — no consistent color system.

### Sparklines everywhere

CPU widget: 12 sparkline charts (one per core), each showing load % over time. Small, inline, no axis labels, just the line + current value.

Network widget: two line graphs (upload, download) showing rate over time.

RAM widget: a single horizontal bar (used/total) — not a chart, but a clear visual.

Storage widget: a donut chart (used/total) — clean, single-value visual.

The RN7 dashboard has no charts at all. Every value is text.

### Layout density

The dashboard uses a grid where each widget grows to fill its column (`cpu_widget_grow: 4`, `ram_widget_grow: 4`, `storage_widget_grow: 3.5`, `network_widget_grow: 6`, `os_widget_grow: 2.5`). The "grow" values control how much horizontal space each widget takes relative to others. This gives a balanced, intentional layout — not a uniform card grid.

The RN7 dashboard uses `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))` — every card is the same minimum width. No intentional sizing hierarchy.

### Toggle controls subtly integrated

- "Dark Mode" toggle — top-left, small, integrated into the OS card
- "Show All Cores" toggle — top of CPU card, expands/collapses per-core detail
- These are inline, not tabs or sidebar items

### Typography and spacing

Clean sans-serif (system font stack), comfortable spacing, no clutter. Each widget has:
- Icon + card title at top
- Key stat (big number) 
- Detail row(s) below
- Visual chart/bar/donut below that

The RN7 dashboard has similar structure (card title + stat + detail) but the execution is sparser.

---

## How it stays smooth — the performance story

### Server-side

1. **One process, one data collection loop** — no per-request fork+exec. The polling loop runs once, pushes to all connected clients via WebSocket.
2. **`systeminformation` is a single library** — no multiple subprocessspawn points. Each widget's poll is one library call.
3. **Background polling is lazy** — starts on connect, stops on disconnect. No collection when no one views.
4. **Static data loaded once** — OS, CPU, RAM layout, storage layout are startup-time. Not per-request.
5. **Network stats via sysfs delta** — two `cat` commands per tick, no ping subprocess.
6. **Configurable intervals** — storage polls at 60s, others at 1s. Not everything at the same rate.

### Client-side

1. **One WebSocket connection** — receives all updates. No multiple HTTP requests per refresh cycle.
2. **React + recharts** — efficient re-rendering. recharts is declarative and only updates changed elements.
3. **Rolling buffer of 20 datapoints** — charts always show the last 20 samples. No history queries, no disk I/O.
4. **Vite-built bundle** — optimized, hashed, cached for 1 year. After first load, no JS/CSS re-download.
5. **Single-page, no route changes** — no page navigation overhead. Widgets update in place.

### Together

The smoothness comes from the **separation of concerns**:
- Data collection is a steady heartbeat (1s for CPU/RAM/network, 60s for storage)
- Transport is a single WebSocket stream
- Rendering is incremental (React + recharts re-render only changed elements)
- No bursty HTTP requests, no per-request subprocess, no page navigation

The user perceives: **connect → see data immediately → data updates smoothly every second → no jank, no loading spinners, no page transitions**.

---

## What the RN7 dashboard does differently (not worse, just different goals)

The RN7 dashboard is a **management dashboard** (start/stop services, kill processes, upgrade packages, reboot, unmount, ping tests) not just a monitoring dashboard. That's a fundamentally different product:
- It needs API endpoints for actions (POST /device/power/reboot, POST /system/services/{name}/start, etc.)
- It needs per-feature pages because each feature has different UI (tables, forms, modals, tabs)
- It needs subprocess calls because the ops it performs (systemctl, upower, ping, apk) are operations, not just reads

Dashdot is **monitoring only** — no actions, no config, no management. It can be lighter because it does less.

---

## What could be borrowed from dashdot for the RN7 dashboard

These are ideas, not instructions — for when the UI/system improvements start:

1. **WebSocket push for real-time widgets** — battery %, CPU freq, thermal zones, network rate could push via WebSocket instead of fetch-on-load. The existing lightweight endpoints + a WebSocket channel would give live updates without re-fetching.

2. **Lazy data collection** — start collecting battery/thermal/cpu data only when a client is connected. Stop when the last client disconnects. This would reduce idle resource usage.

3. **Rolling buffer for sparklines** — keep the last N values of battery %, CPU freq, thermal temps in memory. Render as sparklines on the overview. No history DB needed — just a circular buffer per metric.

4. **`systeminformation`-style unified data library** — instead of 10+ service modules each spawning subprocesses, a single data layer that wraps the system reads. Not a full rewrite, but a unified `get_system_data()` that returns everything in one call.

5. **Sysfs delta for network** — replace ping-based network quality with `/sys/class/net/<iface>/statistics` delta reads. Lighter, more continuous, no subprocess per check.

6. **Static/dynamic split** — device info, CPU model, RAM size, storage layout loaded once at startup. Per-request endpoints only return dynamic values.

7. **Compression + static asset caching** — the RN7 dashboard already uses FastAPI static files, but no compression middleware. Adding `gzip` compression for API responses would reduce payload size.

8. **Widget "grow" layout** — instead of uniform card grid, give each overview card a grow value so important widgets (battery, memory) get more space than less important ones (Hermes status).

9. **Visual polish** — glassmorphism is a style choice, not required. But consistent color coding per widget (one accent color per card), icon + stat + chart hierarchy, and sparklines would elevate the overview from "skeleton" to "real dashboard".

10. **Single-page feel** — the overview page could be the only page for monitoring data, with management actions (services, packages, power) as overlays/modals rather than separate pages. Less page-to-page navigation, more "dashboard + actions".

---

## Bottom line

Dashdot feels light because:
- It's **one process** doing **one thing** (monitoring) with **one data library** (`systeminformation`)
- Data collection is a **steady heartbeat** (WebSocket push, lazy start/stop, configurable intervals)
- The frontend is a **single React page** with **cached assets**, **incremental re-rendering**, and **rolling buffers** for charts
- There are **no actions, no management, no per-feature pages, no subprocess per request**

The RN7 dashboard is a **management dashboard** — heavier by nature. But the monitoring parts (overview, battery, thermal, CPU) could borrow the steady-heartbeat + WebSocket + lazy-collection + sparkline patterns without changing the management features.

---

**Assessment stored:** `/home/rahat/hermes-device-dashboard/DASHDOT_STUDY.md`
