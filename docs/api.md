# API Reference

All API endpoints are mounted under the FastAPI application with the following prefixes:
- `/auth/*` — Authentication and session management
- `/api/system/*` — System services, storage, processes, and logs
- `/api/device/*` — Hardware, network, packages, users, and power controls
- `/api/device/live` — Real-time SSE metric streaming

## Authentication (`/auth/*`)

| Method | Path | Access | Description |
|:---|:---|:---|:---|
| `POST` | `/auth/login` | Public (rate-limited) | Authenticate Linux user credentials. Accepts Form and JSON payloads, sets signed `HttpOnly` cookie. |
| `GET`, `POST` | `/auth/logout` | Authenticated | Terminate session, drop sudo ticket, and clear cookie. |
| `GET` | `/auth/me` | Authenticated | Get current active session details and privilege status. |
| `POST` | `/auth/elevate` | Authenticated | Elevate to administrative privileges (payload: `{"password": "..."}`). |
| `POST` | `/auth/drop-admin` | Authenticated | Drop active elevation and revoke sudo timestamp ticket. |

## System (`/api/system/*`)

| Method | Path | Access | Description |
|:---|:---|:---|:---|
| `GET` | `/api/system/services?scope={user\|system\|all}` | Public | List systemd services. |
| `GET` | `/api/system/services/{service_name}?user={bool}` | Authenticated | Get detailed service status. |
| `GET` | `/api/system/services/{service_name}/logs?lines={n}&user={bool}` | Authenticated | Fetch recent service journal logs. |
| `POST` | `/api/system/services/{service_name}/{action}?user={bool}` | Authenticated (Admin for system) | Run action (`start`, `stop`, `restart`, `enable`, `disable`). |
| `GET` | `/api/system/storage` | Public | Get filesystem and disk usage statistics. |
| `GET` | `/api/system/processes?sort_by={cpu\|mem\|pid\|user\|name}&limit={n}` | Public | Get process list and load averages. |
| `POST` | `/api/system/processes/kill?pid={n}` | Admin | Terminate process by PID. |
| `GET` | `/api/system/memory` | Public | Get human-readable and raw memory statistics. |
| `GET` | `/api/system/logs?lines={n}` | Public | Fetch recent system journal entries. |

## Device & Hardware (`/api/device/*`)

| Method | Path | Access | Description |
|:---|:---|:---|:---|
| `GET` | `/api/device/info` | Public | Get detected device model, OS distribution, kernel, architecture, and hostname. |
| `GET` | `/api/device/network` | Authenticated | Get interface details, WiFi state, DNS servers, gateways, and summary. |
| `GET` | `/api/device/network/ping?target={host}&count={n}` | Authenticated | Perform ping latency test. |
| `GET` | `/api/device/network/dns-query?domain={domain}` | Authenticated | Measure DNS lookup latency. |
| `POST` | `/api/device/network/wifi-scan` | Authenticated | Trigger scan for nearby wireless networks. |
| `GET` | `/api/device/battery` | Public | Get battery status, thermal zones, and CPU frequencies. |
| `GET` | `/api/device/packages` | Authenticated | Get installed package count and upgradable packages. |
| `POST` | `/api/device/packages/upgrade` | Admin | Run package upgrade. |
| `POST` | `/api/device/packages/install?package={name}` | Admin | Install a package. |
| `POST` | `/api/device/packages/remove?package={name}` | Admin | Remove a package. |
| `GET` | `/api/device/packages/search?query={q}` | Authenticated | Search package repository. |
| `GET` | `/api/device/packages/info?package={name}` | Authenticated | Get package details. |
| `GET` | `/api/device/users` | Authenticated | Get system users, all accounts, groups, current user, and sudoers status. |
| `POST` | `/api/device/power/reboot` | Admin | Reboot device. |
| `POST` | `/api/device/power/poweroff` | Admin | Power off device. |
| `POST` | `/api/device/power/suspend` | Admin | Suspend device. |
| `POST` | `/api/device/power/governor?governor={name}` | Admin | Set CPU frequency governor. |
| `GET` | `/api/device/power/state` | Public | Get active CPU governor and scheduled power actions. |
| `POST` | `/api/device/power/schedule` | Admin | Schedule a timed reboot or shutdown. |
| `POST` | `/api/device/power/cancel-scheduled` | Admin | Cancel pending scheduled shutdown or reboot. |

## Live Streaming (SSE)

| Method | Path | Access | Description |
|:---|:---|:---|:---|
| `GET` | `/api/device/live?metrics=cpu,ram,thermal,battery,network` | Public | Real-time Server-Sent Events stream. |

### SSE Event Format
Each event is a JSON object:
```json
{"metric": "cpu", "data": {"cpus": [...], "count": 8, "load1": 0.5}}
```

### Available Metrics
| Metric | Interval | Buffer Size | Description |
|:---|:---|:---|:---|
| `cpu` | 1s | 30 | Per-core usage, frequency, load averages |
| `ram` | 3s | 20 | Total, used, free, swap, percentage |
| `thermal` | 5s | 20 | Multi-zone temperature readings |
| `battery` | 3s | 30 | Capacity, voltage, power draw, temperature |
| `network` | 2s | 30 | RX/TX throughput rates |
