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
| `GET`, `POST` | `/auth/logout` | Public (optional session) | Terminate the session when present, drop the sudo ticket, and clear the cookie. |
| `GET` | `/auth/me` | Authenticated | Get current active session details and privilege status. |
| `POST` | `/auth/elevate` | Authenticated | Elevate to administrative privileges (payload: `{"password": "..."}`). |
| `POST` | `/auth/drop-admin` | Authenticated | Drop active elevation and revoke sudo timestamp ticket. |

## System (`/api/system/*`)

| Method | Path | Access | Description |
|:---|:---|:---|:---|
| `GET` | `/api/system/services?scope={user\|system\|all}` | Optional session | List systemd services. Returns `{services, count}`, each entry tagged with its `scope`. |
| `GET` | `/api/system/services/{service_name}?user={bool}` | Authenticated | Get detailed service status. |
| `GET` | `/api/system/services/{service_name}/logs?lines={n}&user={bool}` | Authenticated | Fetch recent service journal logs. |
| `POST` | `/api/system/services/{service_name}/{action}?user={bool}` | Authenticated (Admin for system) | Run action (`start`, `stop`, `restart`, `enable`, `disable`). |
| `GET` | `/api/system/storage` | Optional session | Get filesystem and disk usage statistics. |
| `GET` | `/api/system/processes?sort_by={cpu\|mem\|pid\|user\|name}&limit={n}` | Optional session | Get process list, load averages, and human-readable memory stats. |
| `POST` | `/api/system/processes/kill?pid={n}` | Admin | Terminate process by PID. |
| `GET` | `/api/system/memory` | Optional session | Get human-readable and raw memory statistics. |
| `GET` | `/api/system/logs?lines={n}` | Optional session | Fetch recent system journal entries. |

## Device & Hardware (`/api/device/*`)

| Method | Path | Access | Description |
|:---|:---|:---|:---|
| `GET` | `/api/device/info` | Optional session | Get detected device model, OS distribution, kernel, architecture, and hostname. |
| `GET` | `/api/device/network` | Authenticated | Get interface details, WiFi state, DNS servers, gateways, and summary. |
| `GET` | `/api/device/network/ping?target={host}&count={n}` | Authenticated | Perform ping latency test. |
| `GET` | `/api/device/network/dns-query?domain={domain}` | Authenticated | Measure DNS lookup latency. |
| `POST` | `/api/device/network/wifi-scan` | Authenticated | Trigger scan for nearby wireless networks. |
| `GET` | `/api/device/battery` | Optional session | Get battery status, thermal zones, CPU frequencies, available CPU scaling governors, and system uptime. |
| `GET` | `/api/device/packages?refresh={bool}&include_list={bool}` | Authenticated | Get package overview: backend info, installed count, upgradable list, and optionally the full installed package list. |
| `POST` | `/api/device/packages/upgrade?package={name}` | Admin | Upgrade all packages, or a single package when `package` is specified. |
| `POST` | `/api/device/packages/install?package={name}` | Admin | Install a package. |
| `POST` | `/api/device/packages/remove?package={name}` | Admin | Remove a package. |
| `GET` | `/api/device/packages/search?query={q}` | Authenticated | Search package repository. |
| `GET` | `/api/device/packages/info?package={name}` | Authenticated | Get package details. |
| `GET` | `/api/device/users` | Authenticated | Get human and system users, categorized groups, active sessions, login history, security posture, and summary metrics. |
| `POST` | `/api/device/users/session/terminate` | Admin | Terminate an active terminal or SSH session. |
| `GET` | `/api/device/users/{username}/ssh-keys` | Authenticated (Self or Admin) | List a user's public SSH keys. |
| `POST` | `/api/device/users/{username}/ssh-keys` | Authenticated (Self or Admin) | Add a public SSH key. |
| `DELETE` | `/api/device/users/{username}/ssh-keys/{key_index}` | Authenticated (Self or Admin) | Delete a public SSH key. |
| `POST` | `/api/device/users/{username}/groups` | Admin | Update a user's secondary groups. |
| `POST` | `/api/device/users/{username}/password` | Authenticated (Self or Admin) | Change a user's password. |
| `POST` | `/api/device/power/reboot` | Admin | Reboot device. |
| `POST` | `/api/device/power/poweroff` | Admin | Power off device. |
| `POST` | `/api/device/power/suspend` | Admin | Suspend device. |
| `POST` | `/api/device/power/governor?governor={name}` | Admin | Set CPU frequency governor. |
| `GET` | `/api/device/power/state` | Optional session | Get active CPU governor and scheduled power actions. |
| `POST` | `/api/device/power/schedule` | Admin | Schedule a timed reboot or shutdown. |
| `POST` | `/api/device/power/cancel-scheduled` | Admin | Cancel pending scheduled shutdown or reboot. |

## Live Streaming (SSE)

| Method | Path | Access | Description |
|:---|:---|:---|:---|
| `GET` | `/api/device/live?metrics=cpu,ram,thermal,battery,network` | Optional session | Real-time Server-Sent Events stream. |

### SSE Event Format
Each event is a JSON object:
```json
{"metric": "cpu", "data": {"cpus": [...], "count": 8, "load1": 0.5}}
```
If metric collection fails, the event omits `data` and includes `error: "collect_failed"`, for example:
```json
{"metric": "cpu", "error": "collect_failed"}
```

### Available Metrics
| Metric | Interval | Buffer Size | Description |
|:---|:---|:---|:---|
| `cpu` | 1s | 30 | Per-core usage, frequency, load averages |
| `ram` | 3s | 20 | Total, used, free, swap, percentage |
| `thermal` | 5s | 20 | Multi-zone temperature readings |
| `battery` | 3s | 30 | Capacity, voltage, power draw, temperature |
| `network` | 2s | 30 | RX/TX throughput rates |

The **SSE push cadence is fixed at 1 s** — the endpoint iterates every
requested metric inside a single `while True` loop with a single
`asyncio.sleep(1)` at the end (`dashboard/api/live.py:48-68`). The per-metric
intervals and buffer sizes above describe each **collector's own polling
cadence** in `dashboard/services/live.py` (`SSE_*_INTERVAL_MS` /
`SSE_*_BUFFER` in `dashboard/config.py`); a slow-changing metric such as
thermal is still pushed every 1 s, it is just collected less often, so its
sparkline buffer receives a fresh value less frequently.

## Access Levels

- **Optional session** — `get_current_session()`: The endpoint works without authentication but may provide additional context or elevated access when a valid session cookie is present. Root users (UID 0) receive permanent elevation.
- **Authenticated** — `require_session()`: Requires a valid signed session cookie.
- **Admin** — `require_admin()`: Requires a valid session with active administrative elevation. Alternatively, an un-elevated but authenticated caller may supply the password inline via the `X-Admin-Password` request header; on successful `sudo -v` validation the session is elevated for the remainder of its timeout window before the request proceeds.
