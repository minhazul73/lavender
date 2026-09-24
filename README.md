![Lavender Banner](https://github.com/user-attachments/assets/d81858ff-fd52-4931-a35d-6a3e8664a655)

# Lavender

A lightweight, responsive FastAPI web dashboard for Linux system management and real-time device monitoring. Built with a sleek dark-theme UI, native Linux PAM authentication, Cockpit-style administrative elevation, and real-time Server-Sent Events (SSE) streaming.

Originally designed for postmarketOS on ARM64 mobile devices (such as the Redmi Note 7 `lavender`), it features dynamic hardware and OS detection that makes it equally well-suited for single-board computers (Raspberry Pi, Pine64), Linux phones, laptops, and home servers.

---

## Features

- **Native Linux Authentication** — Sign in with your standard Linux user credentials via direct PAM, `/etc/shadow`, and `sudo`/`doas` verification. Root accounts (`root` / UID 0) receive automatic permanent elevation, while regular users elevate on demand. No OpenSSH daemon or network loopback sockets required.
- **Role-Based Privilege Elevation** — Cockpit-style admin elevation for users in `wheel`, `sudo`, or `root` groups with temporary 15-minute sudo timestamp tickets. Includes a top-bar status indicator, one-click elevation revocation (`/auth/drop-admin`), and automatic modal prompts when privileged operations are requested.
- **Dynamic Hardware & OS Detection** — Automatically detects hardware/board model (Device Tree, postmarketOS `deviceinfo`, DMI/SMBIOS, `hostnamectl`), OS distribution, kernel version, architecture, and uptime without hardcoded parameters.
- **Live Monitoring via SSE** — Real-time metrics streaming over Server-Sent Events (SSE) with ring-buffered historical sparklines:
  - **CPU:** Real-time per-core usage calculation from `/proc/stat`, live frequencies via cpufreq sysfs, and 1/5/15-minute load averages.
  - **RAM:** Used, free, available, buffers, cache, and swap statistics with percentage gauges.
  - **Thermal:** Multi-zone temperature monitoring across `hwmon`, platform devices, and thermal sysfs with friendly hardware label mapping and warning/critical indicators.
  - **Battery & Power:** Live capacity percentage, charging/discharging states, voltage progress and range indicators, power draw / energy rate (in watts), temperature, time to full/empty, and device metadata via sysfs with UPower fallback.
  - **Network:** Real-time RX/TX throughput rate calculations.
  - **Top Processes Widget:** Auto-refreshing top resource consumers (every 5 seconds) with scrollable container and sticky headers.
- **Distro-Agnostic Package Management** — Multi-backend package management architecture supporting:
  - **Alpine Linux / postmarketOS (`apk`)**
  - **Debian / Ubuntu / Linux Mint (`apt` / `dpkg-query`)**
  - **Arch Linux / Manjaro (`pacman`)**
  - **Fedora / RHEL (`dnf` / `rpm`)**
  - Query installed packages with 60-second in-memory caching, filter upgradable packages, search upstream distribution repositories, inspect detailed package metadata, install or remove packages, and run single-package or complete system upgrades.
- **Identity & Access Control** — Full-featured user, group, and credential management:
  - **User Accounts:** Differentiates interactive human users (UID ≥ 1000) from system and service accounts, including home storage partition capacity (total, used, free GB, and usage percentage).
  - **SSH Key Management:** View, add, and delete public keyhttps://github.com/user-attachments/assets/d81858ff-fd52-4931-a35d-6a3e8664a655s in `~/.ssh/authorized_keys` directly through modal dialogs.
  - **Active Sessions:** Track active terminal and SSH sessions (`who -u`, TTY, host IP, login time, idle state) with one-click remote session termination.
  - **Password Updates:** Self-service password changes for authenticated users and administrative password resets.
  - **Group & Hardware Access:** Categorized Linux group inspection and member editing across Privileged (`wheel`, `sudo`, `docker`), Hardware subsystems (`audio`, `video`, `netdev`, `input`, `bluetooth`), Service daemons (`nginx`, `caddy`, `postgres`), and System groups.
  - **Security Posture:** Audits elevation engines (`sudo` / `doas`), `visudo -c` syntax validation, OpenSSH daemon status (`sshd`), `PermitRootLogin`, `PasswordAuthentication` settings, and recent login history via `last`.
- **Power Management & CPU Profiles** — System lifecycle operations and energy profile controls:
  - **System Lifecycle:** Clean, modal-confirmed `reboot`, `poweroff`, and `suspend` operations protected by administrative elevation.
  - **CPU Power Profiles:** Live governor detection and one-click switching across all CPU cores (`powersave`, `schedutil` / `ondemand`, `performance`).
  - **Scheduled Power Actions:** Quick-timer presets (5m, 15m, 30m, 60m), custom countdown timers with broadcast wall messages (`shutdown -r +N`, `shutdown -h +N`), live pending schedule status banner, and one-click cancellation (`shutdown -c`).
- **Systemd Service Management** — Manage system and user services (`systemctl` and `systemctl --user`). Filter by scope (`user`, `system`, `all`) and state (`active`, `inactive`, `failed`), navigate with pagination, inspect unit status, view real-time journalctl logs in an embedded dark terminal window with copyable commands, and execute lifecycle actions (`start`, `stop`, `restart`, `enable`, `disable`).
- **Storage & Mounts** — Disk usage overview with visual usage bars, automatic filtering of pseudo/virtual filesystems (`tmpfs`, `devpts`), and external storage detection (`/mnt`, `/media`, `/sdcard`).
- **Process Management** — Interactive process monitor with sorting by CPU, memory, PID, user, or name, supporting both standard `procps` and `busybox ps`. Terminate processes with admin privileges (`kill -9`).
- **Network & Diagnostics** — 
  - Detailed interface status with IPv4, IPv6, MAC, MTU, carrier state, and RX/TX packet & byte counters.
  - WiFi status and nearby network scanning supporting `nmcli`, `iw`, `iwconfig`, `wpa_cli`, and `/proc/net/wireless` (SSID, BSSID, signal strength, channel, frequency, bitrate, and security).
  - DNS configuration with automatic provider identification (Cloudflare, Google, Quad9, AdGuard, OpenDNS, Local Gateway).
  - Interactive ping latency tests and domain resolution latency queries.
  - Default route and gateway discovery.

---

## Tech Stack

- **Backend:** FastAPI (async) + Uvicorn
- **Frontend:** Vanilla JavaScript (ES6+, no frameworks) + Jinja2 templates
- **Styling:** Custom responsive CSS, dark theme, Lavender theme palette (`--lavender-*`, `--grad-lavender`, glassmorphism, accent glow effects, micro-animations)
- **Real-time:** Server-Sent Events (SSE) via FastAPI `StreamingResponse` and background `MetricCollector` ring buffers
- **Package Management:** Multi-backend adapter architecture (`apk`, `apt`, `pacman`, `dnf`) with in-memory TTL caching
- **Authentication:** Native Linux PAM (`python-pam`), shadow verification, `sudo -v` timestamp tickets, signed cookies (`itsdangerous`)
- **Rate Limiting:** `slowapi` brute-force protection on authentication endpoints
- **Runtime:** Python 3.11+, runs as a systemd user or system service

---

## Quick Start

### Prerequisites

- Linux operating system (postmarketOS / Alpine, Debian, Ubuntu, Fedora, Arch, etc.)
- Python 3.11+
- PAM development libraries (e.g., `linux-pam-dev` on Alpine/postmarketOS, `libpam0g-dev` on Debian/Ubuntu)
- `sudo` (or `doas`) for administrative operations
- `systemd` (with `systemctl --user` support for user services)

### Installation

```bash
git clone https://github.com/minhazul73/lavender.git
cd lavender
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running

**Manual / Development:**
```bash
python -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080 --reload
```

**As a systemd service:**
An example service file is provided in [`systemd/lavender.service`](systemd/lavender.service).

To install as a systemd user service:
```bash
mkdir -p ~/.config/systemd/user/
cp systemd/lavender.service ~/.config/systemd/user/
# Edit WorkingDirectory and ExecStart paths in ~/.config/systemd/user/lavender.service to match your environment
systemctl --user daemon-reload
systemctl --user enable --now lavender
```

### Access

Open `http://<device-ip>:8080` in your web browser. 
- The **Overview** page (`/`) is publicly viewable without authentication for quick device telemetry.
- Protected pages and administrative actions require signing in with your Linux system credentials.

---

## Authentication & Security

Lavender authenticates directly against your host Linux operating system:

1. **Native Verification:** When logging in via `/auth/login`, credentials are validated in sequence against:
   - Direct `/etc/shadow` verification (if accessible)
   - Linux PAM services (`PAM_SERVICE`, fallback to `base-auth`, `login`, etc.)
   - Sudo credential check (`sudo -S -p '' -v`)
   - Doas validation (`doas -C /etc/doas.conf true`)
2. **Session Storage:** A cryptographically signed session cookie (`rn7_session`) is issued using `itsdangerous`. Sessions are stored in-memory with a sliding 60-minute idle expiration.
3. **Background Cleanup:** A background task runs every 5 minutes to purge expired idle sessions.
4. **Cockpit-style Elevation:** Users in administrative groups (`wheel`, `sudo`, `root` or UID 0) can elevate their session by entering their password. This refreshes a local sudo timestamp ticket for 15 minutes. Root sessions (UID 0 / `root`) are automatically elevated permanently.
5. **Elevation Revocation:** Non-root users can revoke elevation at any time via the top bar "Turn off" button, which calls `/auth/drop-admin` and runs `sudo -k` to drop the timestamp ticket.
6. **Rate Limiting:** Login requests are rate-limited to 10 requests per minute via `slowapi` to mitigate brute-force attempts.

---

## Configuration

Configuration values are located in [`dashboard/config.py`](dashboard/config.py) and can be customized directly or via environment variables:

### General Settings
| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `8080` | Web server port |
| `HOST` | `"0.0.0.0"` | Bind network interface |
| `DEBUG` | `False` | Debug mode toggle |
| `APP_VERSION` | `"0.4.0"` | Application version |
| `THERMAL_WARN_THRESHOLD` | `70000` | Thermal warning threshold in millidegrees C (70°C) |
| `MEMORY_PRESSURE_THRESHOLD`| `0.85` | RAM fraction used to trigger memory pressure warning (85%) |
| `LOG_LINES` | `50` | Default number of log lines to return |
| `TOP_PROCESSES` | `20` | Default process limit |
| `TOP_DIRS` | `10` | Top directories limit for disk usage |

### Auth & Session Settings
| Variable | Default | Description |
| :--- | :--- | :--- |
| `SESSION_COOKIE_NAME` | `"rn7_session"` | Session cookie name |
| `SESSION_MAX_IDLE_MINUTES` | `60` | Inactivity timeout before session expires |
| `ADMIN_ELEVATION_TIMEOUT_MINUTES` | `15` | Administrative elevation duration |
| `SESSION_SECRET_KEY` | *(env or default)* | Cookie signing key (set via `DASHBOARD_SECRET_KEY`) |
| `PAM_SERVICE` | `"login"` | Primary PAM service name (set via `PAM_SERVICE`) |
| `LOGIN_RATE_LIMIT` | `"10/minute"` | Rate limit for login endpoint |

### SSE Live Monitoring Intervals & Buffers
| Variable | Default | Description |
| :--- | :--- | :--- |
| `SSE_CPU_INTERVAL_MS` | `1000` | CPU metrics collection interval (1s) |
| `SSE_RAM_INTERVAL_MS` | `3000` | RAM metrics collection interval (3s) |
| `SSE_THERMAL_INTERVAL_MS` | `5000` | Thermal zones collection interval (5s) |
| `SSE_BATTERY_INTERVAL_MS` | `3000` | Battery metrics collection interval (3s) |
| `SSE_NETWORK_INTERVAL_MS` | `2000` | Network rate collection interval (2s) |
| `SSE_*_BUFFER` | `20`–`30` | Datapoints retained in ring buffers for sparklines |

---

## Web UI Pages

| Route | Page Name | Access | Description |
| :--- | :--- | :--- | :--- |
| `/` | Overview | Public | Device telemetry overview, live gauges, specs, top processes with auto-refresh, and status |
| `/login` | Sign In | Public | System user authentication page |
| `/services` | Services | Protected | Systemd user and system service control, pagination, filtering, and terminal log viewer |
| `/processes`| Processes | Protected | Interactive process list, load averages, memory info, and process kill actions |
| `/storage` | Storage | Protected | Filesystem and disk usage breakdown, mount points, and top directory analysis |
| `/network` | Network | Protected | Network adapters, WiFi scanning, DNS info, ping & DNS latency tools |
| `/packages` | Packages & Updates | Protected | Distro-agnostic package management (`apk`, `apt`, `pacman`, `dnf`), updates, repo search, info, install, and remove |
| `/users` | Users & Permissions | Protected | Accounts (human vs system), active TTY/SSH sessions, group management, SSH keys, password changes, and security posture |
| `/power` | Power Management | Protected | System reboot, power off, suspend, CPU power profiles/governors, and scheduled power actions |
| `/battery` | Redirect | Public | Redirects (307) to `/` (battery widget is integrated into Overview) |

---

## API Reference

### Authentication (`/auth/*`)
- `POST /auth/login` — Authenticate user credentials (supports Form and JSON payloads; sets signed cookie)
- `GET, POST /auth/logout` — Terminate session, drop sudo ticket, and clear cookie
- `GET /auth/me` — Get current active session details and privilege status
- `POST /auth/elevate` — Elevate to administrative privileges (payload: `{"password": "..."}`)
- `POST /auth/drop-admin` — Drop active elevation and revoke sudo timestamp ticket

### System (`/api/system/*`)
- `GET /api/system/services?scope={user|system|all}` — List systemd services
- `GET /api/system/services/{service_name}?user={bool}` — Get detailed service status
- `GET /api/system/services/{service_name}/logs?lines={n}&user={bool}` — Fetch recent service journal logs
- `POST /api/system/services/{service_name}/{action}?user={bool}` — Run action (`start`, `stop`, `restart`, `enable`, `disable`)
- `GET /api/system/storage` — Get filesystem and disk usage statistics
- `GET /api/system/processes?sort_by={cpu|mem|pid|user|name}&limit={n}` — Get process list and load averages
- `POST /api/system/processes/kill?pid={n}` — Terminate process by PID *(admin required)*
- `GET /api/system/memory` — Get human-readable and raw memory statistics
- `GET /api/system/logs?lines={n}` — Fetch recent system journal entries

### Device, Hardware & Management (`/api/device/*`)

#### System & Hardware Info
- `GET /api/device/info` — Get detected device model, OS distribution, kernel, architecture, and hostname

#### Network & Connectivity
- `GET /api/device/network` — Get interface details, WiFi state, DNS servers, gateways, and summary
- `GET /api/device/network/ping?target={host}&count={n}` — Perform ping latency test
- `GET /api/device/network/dns-query?domain={domain}` — Measure DNS lookup latency
- `POST /api/device/network/wifi-scan` — Trigger scan for nearby wireless networks

#### Battery & Hardware Telemetry
- `GET /api/device/battery` — Get battery status, thermal zones, and CPU frequencies

#### Package Management (Distro-Agnostic)
- `GET /api/device/packages` — Get installed package count, manager backend, and upgradable packages
- `GET /api/device/packages/search?query={q}` — Search package repository
- `GET /api/device/packages/info?package={name}` — Get detailed package information and description
- `POST /api/device/packages/upgrade` — Upgrade all packages or a specific package *(admin required; optional payload: `{"package": "..."}`)*
- `POST /api/device/packages/install` — Install a package *(admin required; payload: `{"package": "..."}`)*
- `POST /api/device/packages/remove` — Remove an installed package *(admin required; payload: `{"package": "..."}`)*

#### Identity, Sessions & SSH
- `GET /api/device/users` — Get regular human users, system accounts, group memberships, active sessions, and security posture
- `POST /api/device/users/session/terminate` — Terminate an active terminal/SSH session *(admin required; payload: `{"tty": "...", "pid": ...}`)*
- `GET /api/device/users/{username}/ssh-keys` — List SSH public keys in `authorized_keys` for user
- `POST /api/device/users/{username}/ssh-keys` — Add an SSH public key *(admin required; payload: `{"key": "..."}`)*
- `DELETE /api/device/users/{username}/ssh-keys/{key_index}` — Delete an SSH public key *(admin required)*
- `POST /api/device/users/{username}/groups` — Update user group memberships *(admin required; payload: `{"groups": [...]}`)*
- `POST /api/device/users/{username}/password` — Update user password *(self or admin required; payload: `{"current_password": "...", "new_password": "..."}`)*

#### Power Management & Governors
- `GET /api/device/power/state` — Get full power state (battery, thermal, current and available CPU governors, scheduled power actions)
- `POST /api/device/power/governor` — Set CPU frequency scaling governor across all cores *(admin required; payload: `{"governor": "..."}`)*
- `POST /api/device/power/schedule` — Schedule a reboot or poweroff in N minutes *(admin required; payload: `{"action": "reboot|poweroff", "minutes": n, "message": "..."}`)*
- `POST /api/device/power/cancel-scheduled` — Cancel a pending scheduled reboot or poweroff *(admin required)*
- `POST /api/device/power/reboot` — Reboot device *(admin required)*
- `POST /api/device/power/poweroff` — Power off device *(admin required)*
- `POST /api/device/power/suspend` — Suspend device *(admin required)*

### Live Streaming (SSE)
- `GET /api/device/live?metrics=cpu,ram,thermal,battery,network` — Real-time Server-Sent Events stream for subscribed metrics

---

## Project Structure

```
lavender/
├── dashboard/
│   ├── main.py                  # FastAPI application, lifespan, page routes, and middleware
│   ├── config.py                # Configuration constants, intervals, thresholds, and limits
│   ├── dependencies.py          # Command runners, session execution, and system utility helpers
│   ├── auth/
│   │   ├── __init__.py          # Auth module init
│   │   ├── bridge.py            # Linux PAM, shadow, and sudo/doas execution engine
│   │   ├── session.py           # In-memory session store with signed cookie serializer
│   │   └── deps.py              # FastAPI dependencies (require_session, require_admin)
│   ├── api/
│   │   ├── auth.py              # Authentication endpoints (/auth/*)
│   │   ├── system.py            # System endpoints (/api/system/*)
│   │   ├── device.py            # Device, packages, users, SSH, and power endpoints (/api/device/*)
│   │   └── live.py              # Server-Sent Events (SSE) live streaming endpoint
│   ├── services/
│   │   ├── device_info.py       # Dynamic hardware model, OS, and kernel discovery
│   │   ├── live.py              # SSE MetricCollector base, RingBuffer, and collectors
│   │   ├── systemd.py           # systemctl and journalctl wrappers
│   │   ├── storage.py           # df -h parsing, mounts, and directory usage
│   │   ├── processes.py         # ps aux and /proc resource inspection
│   │   ├── network.py           # Interfaces, WiFi tools, DNS info, ping, and DNS queries
│   │   ├── battery.py           # UPower and sysfs battery/thermal queries, CPU governors
│   │   ├── packages.py          # Distro-agnostic package manager (apk, apt, pacman, dnf)
│   │   ├── power.py             # System power actions and scheduled shutdown wrappers
│   │   └── users.py             # User accounts, SSH keys, sessions, and security posture
│   ├── templates/
│   │   ├── base.html            # Core layout, sidebar navigation, top bar, and elevation modal
│   │   ├── index.html           # Real-time overview dashboard with live metric cards & top processes
│   │   ├── login.html           # System login form
│   │   ├── services.html        # Systemd service manager with terminal log viewer & pagination
│   │   ├── storage.html         # Disk usage, mount points, and directory usage
│   │   ├── processes.html       # Running processes and resource monitor
│   │   ├── network.html         # Network cards, WiFi info, nearby APs, and ping/DNS diagnostics
│   │   ├── packages.html        # Package updates, search, details, install, and remove
│   │   ├── users.html           # Users, active sessions, groups, SSH keys, and security posture
│   │   ├── power.html           # System power actions, CPU power profiles, and scheduled timers
│   │   └── battery.html         # Battery template (redirected to Overview)
│   └── static/
│       ├── style.css            # Base stylesheet (Lavender theme, components, typography)
│       ├── live.css             # Live metric card styling, battery bars, network widgets
│       ├── script.js            # Frontend utilities, modal controllers, admin elevation toggles
│       └── live.js              # EventSource SSE client, real-time DOM updater, sparklines
├── systemd/
│   └── lavender.service         # systemd user service unit template
├── requirements.txt             # Python project dependencies
├── CONTRIBUTING.md              # Contribution guidelines
├── LICENSE                      # MIT License
└── README.md                    # Project documentation
```

---

## Limitations & Notes

1. **Package Management:** Lavender features a distro-agnostic package adapter framework with support for Alpine / postmarketOS (`apk`), Debian / Ubuntu (`apt`), Arch Linux (`pacman`), and Fedora / RHEL (`dnf`). If an unsupported package manager is present, package management gracefully falls back to a disabled state.
2. **Kernel Sysfs Features:** Certain metrics (such as dynamic CPU frequency scaling or battery power draw) require kernel driver support in `/sys/devices/system/cpu/*/cpufreq` or `/sys/class/power_supply`. On virtual machines or devices without battery or cpufreq drivers, these cards gracefully indicate that the sensor data is unavailable.
3. **Privileged Actions:** Modifying system services, killing processes, installing/upgrading packages, editing user groups/keys, adjusting CPU governors, and triggering power operations require administrative privileges (`wheel` or `sudo` membership) and sudo configured on the host. Root accounts (UID 0) are automatically granted permanent elevation.

---

## Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on code style, testing, and pull requests.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Credits

Created with ❤️ for postmarketOS on Redmi Note 7 and Linux devices by [rahat](https://github.com/minhazul73).
Powered by FastAPI, Uvicorn, and vanilla JavaScript.
