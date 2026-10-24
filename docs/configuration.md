# Configuration Reference

All Lavender configuration constants are defined in [`server/core/config.py`](file:///home/rahat/Documents/vscode/FASTAPI/lavender/server/core/config.py). Settings can be customized via environment variables or a `.env` file.

---

## Environment Variables

### Network & Server Settings

| Variable | Default | Description |
|:---|:---|:---|
| `LAVENDER_PORT` / `PORT` | `8080` | Port for the FastAPI web server |
| `LAVENDER_HOST` / `HOST` | `"0.0.0.0"` | Bind network interface (`0.0.0.0` binds all interfaces) |
| `LAVENDER_DEBUG` | `False` | Enable debug mode (`true`/`false` or `1`/`0`) |
| `APP_VERSION` | `"0.4.0"` | Current application version |

### Authentication & Sessions

| Variable | Default | Description |
|:---|:---|:---|
| `SESSION_COOKIE_NAME` | `"lavender_session"` | Name of the signed HTTP session cookie |
| `SESSION_MAX_IDLE_MINUTES` | `60` | Maximum inactivity duration (in minutes) before session expires |
| `ADMIN_ELEVATION_TIMEOUT_MINUTES` | `15` | Sudo elevation ticket lifetime (in minutes) before re-auth is needed |
| `LAVENDER_SECRET_KEY` / `DASHBOARD_SECRET_KEY` | *(built-in fallback)* | Secret key used by `itsdangerous` to sign session cookies |
| `PAM_SERVICE` | `"login"` | Primary PAM service name for authentication (falls back to `base-auth` or `/etc/shadow`) |
| `LOGIN_RATE_LIMIT` | `"10/minute"` | Brute-force rate limit enforced by `slowapi` on `/auth/login` |

### System Thresholds & Limits

| Setting | Default | Description |
|:---|:---|:---|
| `THERMAL_WARN_THRESHOLD` | `70000` | Thermal warning threshold in millidegrees Celsius (70°C) |
| `MEMORY_PRESSURE_THRESHOLD` | `0.85` | Fraction of total RAM used before triggering high-memory warning (85%) |
| `LOG_LINES` | `50` | Default number of journalctl log lines to fetch |
| `TOP_PROCESSES` | `20` | Default number of processes returned in process queries |
| `TOP_DIRS` | `10` | Number of top space-consuming directories returned by storage analysis |

---

## Server-Sent Events (SSE) Live Telemetry Intervals

Each metric collector runs on an independent polling cycle. Tuning these values allows you to balance real-time responsiveness against CPU utilization on low-power devices:

| Setting | Default Interval | Rolling Buffer Size | Monitored Metric |
|:---|:---|:---|:---|
| `SSE_CPU_INTERVAL_MS` | `1000` (1s) | `30` points | Per-core usage & scaling frequencies |
| `SSE_RAM_INTERVAL_MS` | `3000` (3s) | `20` points | Memory and swap usage |
| `SSE_THERMAL_INTERVAL_MS` | `5000` (5s) | `20` points | Hardware thermal zones |
| `SSE_BATTERY_INTERVAL_MS` | `3000` (3s) | `30` points | Battery capacity, voltage & power draw |
| `SSE_NETWORK_INTERVAL_MS` | `2000` (2s) | `30` points | Interface RX/TX throughput rate |

---

## Overriding Configuration

### Using Environment Variables
You can pass environment variables directly when launching Lavender:

```bash
LAVENDER_PORT=9090 LAVENDER_SECRET_KEY="your-custom-production-key" lavender
```

### Using Systemd Service Environment
When running under systemd, configure environment variables in your unit file or via `systemctl edit`:

```ini
[Service]
Environment="LAVENDER_PORT=8080"
Environment="LAVENDER_SECRET_KEY=your-production-secret-here"
Environment="PAM_SERVICE=system-auth"
```
