![Lavender Banner](https://github.com/user-attachments/assets/d81858ff-fd52-4931-a35d-6a3e8664a655)

# Lavender

A lightweight, modern web dashboard for Linux system management and real-time device monitoring. Built with a decoupled **FastAPI** modular backend and a sleek **React 18 + TypeScript** Single-Page Application (SPA) frontend, featuring native Linux PAM authentication, Cockpit-style administrative elevation, real-time Server-Sent Events (SSE) streaming, a built-in web file manager, and distro-agnostic package management.

Originally designed for postmarketOS on ARM64 mobile devices (such as the Redmi Note 7 `lavender`), Lavender features dynamic hardware and OS detection that makes it equally well-suited for single-board computers (Raspberry Pi, Pine64, Orange Pi), Linux phones, laptops, home servers, and cloud instances.

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
  - **Network:** Real-time RX/TX throughput rate calculations with automatic deprioritization of virtual/VPN interfaces (e.g., Tailscale).
  - **Top Processes Widget:** Auto-refreshing top resource consumers (every 5 seconds) with scrollable container and sticky headers.
- **Storage & Web File Manager** — Comprehensive storage management and interactive file browser:
  - **Filesystem Overview:** Disk partition usage bars, mount point inspection, external drive detection (`/mnt`, `/media`, `/sdcard`), and partition unmounting (`/api/storage/unmount`).
  - **Interactive File Browser:** Directory tree navigation with breadcrumb trail, quick-access drive shortcuts and bookmarks, search/filter files by name.
  - **File Viewer & Editor:** In-browser text file viewer and editor with syntax display and live save support.
  - **Media Preview & Download:** Direct raw streaming and downloading of files, images, documents, and media.
  - **File Operations:** Create files, create folders (`mkdir`), rename, and batch/single delete with safety confirmations.
  - **File Upload:** Upload single or multiple files directly to any destination folder.
- **Distro-Agnostic Package Management** — Multi-backend package management architecture supporting:
  - **Alpine Linux / postmarketOS (`apk`)**
  - **Debian / Ubuntu / Linux Mint (`apt` / `dpkg-query`)**
  - **Arch Linux / Manjaro (`pacman`)**
  - **Fedora / RHEL (`dnf` / `rpm`)**
  - Query installed packages with 60-second in-memory caching, filter upgradable packages, search upstream distribution repositories, inspect detailed package metadata, install or remove packages, and run single-package or complete system upgrades.
- **Identity & Access Control** — Full-featured user, group, and credential management:
  - **User Accounts:** Differentiates interactive human users (UID ≥ 1000) from system and service accounts, including home storage partition capacity (total, used, free GB, and usage percentage).
  - **SSH Key Management:** View, add, and delete public keys in `~/.ssh/authorized_keys` directly through modal dialogs.
  - **Active Sessions:** Track active terminal and SSH sessions (`who -u`, TTY, host IP, login time, idle state) with one-click remote session termination.
  - **Password Updates:** Self-service password changes for authenticated users and administrative password resets.
  - **Group & Hardware Access:** Categorized Linux group inspection and member editing across Privileged (`wheel`, `sudo`, `docker`), Hardware subsystems (`audio`, `video`, `netdev`, `input`, `bluetooth`), Service daemons (`nginx`, `caddy`, `postgres`), and System groups.
  - **Security Posture:** Audits elevation engines (`sudo` / `doas`), `visudo -c` syntax validation, OpenSSH daemon status (`sshd`), `PermitRootLogin`, `PasswordAuthentication` settings, and recent login history via `last`.
- **Power Management & CPU Profiles** — System lifecycle operations and energy profile controls:
  - **System Lifecycle:** Clean, modal-confirmed `reboot`, `poweroff`, and `suspend` operations protected by administrative elevation.
  - **CPU Power Profiles:** Live governor detection and one-click switching across all CPU cores (`powersave`, `schedutil` / `ondemand`, `performance`).
  - **Scheduled Power Actions:** Quick-timer presets (5m, 15m, 30m, 60m), custom countdown timers with broadcast wall messages (`shutdown -r +N`, `shutdown -h +N`), live pending schedule status banner, and one-click cancellation (`shutdown -c`).
- **Systemd Service Management** — Manage system and user services (`systemctl` and `systemctl --user`). Filter by scope (`user`, `system`, `all`) and state (`active`, `inactive`, `failed`), navigate with pagination, inspect unit status, view real-time journalctl logs in an embedded dark terminal window with copyable commands, and execute lifecycle actions (`start`, `stop`, `restart`, `enable`, `disable`).
- **Process Management** — Interactive process monitor with sorting by CPU, memory, PID, user, or name, supporting both standard `procps` and `busybox ps`. Expandable row details with instant command copy and safe process termination (`kill -9`).
- **Network & Diagnostics** — 
  - Detailed interface status with IPv4, IPv6, MAC, MTU, carrier state, and RX/TX packet & byte counters (with virtual/Tailscale interfaces deprioritized).
  - WiFi status and nearby network scanning supporting `nmcli`, `iw`, `iwconfig`, `wpa_cli`, and `/proc/net/wireless` (SSID, BSSID, signal strength, channel, frequency, bitrate, and security).
  - DNS configuration with automatic provider identification (Cloudflare, Google, Quad9, AdGuard, OpenDNS, Local Gateway).
  - Interactive ping latency tests and domain resolution latency queries.
  - Default route and gateway discovery.
- **Mobile-First Responsive Design** — Built to look and feel like a native application across all form factors:
  - Dynamic viewport height (`--dvh`) handling that adapts seamlessly to mobile browser URL bars and virtual keyboards.
  - Safe area inset support (`env(safe-area-inset-*)`) for notched displays on mobile Linux phones (e.g. Redmi Note 7, PinePhone).
  - Collapsible desktop sidebar with persistent state and mobile bottom navigation drawer.
  - Touch-friendly controls, responsive data tables with mobile card view fallbacks, and glassmorphic modal workflows.

---

## Tech Stack

- **Backend:** FastAPI (async) + Uvicorn + Pydantic v2 + Python 3.11+
- **Frontend:** React 18 + TypeScript + Vite + Lucide React + Bun
- **Zero Runtime Overhead on Embedded Devices:** Pre-compiled, minified production assets live in `server/dist/`. Linux SBCs and phones do **not** need Node.js, Bun, or npm installed to run Lavender.
- **Styling:** Custom responsive CSS, dark theme, Lavender theme palette (`--lavender-*`, `--grad-lavender`, glassmorphism, accent glow effects, micro-animations)
- **Real-time:** Server-Sent Events (SSE) via FastAPI `StreamingResponse` and background `MetricCollector` ring buffers
- **Package Management:** Multi-backend adapter architecture (`apk`, `apt`, `pacman`, `dnf`) with in-memory TTL caching
- **Authentication:** Native Linux PAM (`python-pam`), `/etc/shadow` fallback, `sudo -v` timestamp tickets, signed cookies (`itsdangerous`)
- **Rate Limiting:** `slowapi` brute-force protection on authentication endpoints
- **Testing:** 140+ automated tests across `pytest` (backend unit & integration) and `vitest` (frontend components & hooks)

---

## Quick Start

### Prerequisites

- Linux operating system (postmarketOS / Alpine, Debian, Ubuntu, Fedora, Arch, etc.)
- Python 3.11+
- PAM development libraries (e.g., `linux-pam-dev` on Alpine/postmarketOS, `libpam0g-dev` on Debian/Ubuntu)
- `sudo` (or `doas`) for administrative operations
- `systemd` (with `systemctl --user` support for user services)

### Installation

#### Using `uv` (Recommended)

```bash
git clone https://github.com/minhazul73/lavender.git
cd lavender
uv sync --extra dev
```

#### Using Standard `pip` & `venv`

```bash
git clone https://github.com/minhazul73/lavender.git
cd lavender
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running

**Production Server (Precompiled SPA bundle):**
```bash
# Using the installed CLI entry point
lavender

# Or running directly with uvicorn
uv run uvicorn server.main:app --host 0.0.0.0 --port 8080
```

**Development Environment (with Hot-Reload & HMR):**
```bash
# Install all dependencies (backend + frontend)
make install

# Terminal 1: Backend API server (runs on port 8085 with auto-reload)
make dev-backend

# Terminal 2: Vite frontend server (runs on port 3000, proxies /api and /auth to :8085)
make dev-frontend
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

Open `http://<device-ip>:8080` in your web browser (or `http://localhost:3000` during development).
- The **Overview** page (`/`) provides immediate device telemetry.
- Protected management pages and administrative actions authenticate using your standard Linux user credentials.

---

## Authentication & Security

Lavender authenticates directly against your host Linux operating system:

1. **Native Verification:** When logging in via `/auth/login`, credentials are validated in sequence against:
   - Direct `/etc/shadow` verification (if accessible)
   - Linux PAM services (`PAM_SERVICE`, fallback to `base-auth`, `login`, etc.)
   - Sudo credential check (`sudo -S -p '' -v`)
   - Doas validation (`doas -C /etc/doas.conf true`)
2. **Session Storage:** A cryptographically signed session cookie (`lavender_session`) is issued using `itsdangerous`. Sessions are stored in-memory with a sliding 60-minute idle expiration.
3. **Background Cleanup:** An asynchronous background task runs every 5 minutes to purge expired idle sessions.
4. **Cockpit-style Elevation:** Users in administrative groups (`wheel`, `sudo`, `root` or UID 0) can elevate their session by entering their password. This refreshes a local sudo timestamp ticket for 15 minutes. Root sessions (UID 0 / `root`) are automatically elevated permanently.
5. **Elevation Revocation:** Non-root users can revoke elevation at any time via the top bar "Turn off" button, which calls `/auth/drop-admin` and runs `sudo -k` to drop the timestamp ticket.
6. **Rate Limiting:** Login requests are rate-limited to 10 requests per minute via `slowapi` to mitigate brute-force attempts.

---

## Configuration

Configuration values are defined in [`server/core/config.py`](server/core/config.py) and can be customized directly or via environment variables:

### General Settings
| Variable | Default | Description |
| :--- | :--- | :--- |
| `LAVENDER_PORT` / `PORT` | `8080` | Web server port |
| `LAVENDER_HOST` / `HOST` | `"0.0.0.0"` | Bind network interface |
| `LAVENDER_DEBUG` | `False` | Debug mode toggle (`true`/`false`) |
| `APP_VERSION` | `"0.4.0"` | Application version |
| `THERMAL_WARN_THRESHOLD` | `70000` | Thermal warning threshold in millidegrees C (70°C) |
| `MEMORY_PRESSURE_THRESHOLD`| `0.85` | RAM fraction used to trigger memory pressure warning (85%) |
| `LOG_LINES` | `50` | Default number of log lines to return |
| `TOP_PROCESSES` | `20` | Default process limit |
| `TOP_DIRS` | `10` | Top directories limit for disk usage |

### Auth & Session Settings
| Variable | Default | Description |
| :--- | :--- | :--- |
| `SESSION_COOKIE_NAME` | `"lavender_session"` | Session cookie name |
| `SESSION_MAX_IDLE_MINUTES` | `60` | Inactivity timeout before session expires |
| `ADMIN_ELEVATION_TIMEOUT_MINUTES` | `15` | Administrative elevation duration |
| `LAVENDER_SECRET_KEY` / `DASHBOARD_SECRET_KEY` | *(default)* | Cookie signing key |
| `PAM_SERVICE` | `"login"` | Primary PAM service name |
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
| `/` | **Overview** | Public / Protected | Real-time telemetry overview, live gauges, specs chip, network sparkline, and top processes widget |
| `/login` | **Sign In** | Public | System user authentication page with pam/shadow validation |
| `/services` | **Services** | Protected | Systemd user and system service control, search, scope/state filtering, pagination, and terminal log viewer |
| `/processes`| **Processes** | Protected | Interactive process monitor with multi-column sorting, expandable command details with copy, and PID termination |
| `/storage` | **Storage** | Protected | Partition usage gauges, mount points, unmount actions, and full-featured **Web File Browser** (view, edit, raw stream, mkdir, create, rename, delete, upload) |
| `/network` | **Network** | Protected | Network adapters (deprioritizing Tailscale), WiFi scanning with signal indicators, DNS info, ping & DNS latency diagnostic tools |
| `/packages` | **Packages** | Protected | Distro-agnostic package management (`apk`, `apt`, `pacman`, `dnf`), updates, repo search, info, install, and remove |
| `/users` | **Users** | Protected | Accounts (human vs system), active TTY/SSH sessions with termination, group management, SSH keys, password changes, and security posture |
| `/power` | **Power** | Protected | System reboot, power off, suspend, CPU power profiles/governors, and scheduled power actions with countdowns and cancellations |

---

## API Reference

### Authentication (`/auth/*`)
- `POST /auth/login` — Authenticate user credentials (supports Form and JSON payloads; sets signed cookie)
- `GET, POST /auth/logout` — Terminate session, drop sudo ticket, and clear cookie
- `GET /auth/me` — Get current active session details and privilege status
- `POST /auth/elevate` — Elevate to administrative privileges (payload: `{"password": "..."}`)
- `POST /auth/drop-admin` — Drop active elevation and revoke sudo timestamp ticket

### Storage & Web File Browser (`/api/storage/*`)
- `GET /api/storage` — Get disk partitions, mount usage, and directory stats
- `POST /api/storage/unmount` — Unmount a partition or device *(admin required; payload: `{"mount_point": "..."}`)*
- `GET /api/storage/files?path={path}` — List files and directories with metadata (size, permissions, timestamps)
- `GET /api/storage/bookmarks` — Get quick-access navigation bookmarks and external drive shortcuts
- `GET /api/storage/file/view?path={path}` — Preview or read text file content (with line limit)
- `GET /api/storage/file/raw?path={path}` — Download or stream raw file content for media preview
- `POST /api/storage/file/save` — Save edited text file content *(admin required for protected files; payload: `{"path": "...", "content": "..."}`)*
- `POST /api/storage/mkdir` — Create a new directory *(payload: `{"path": "...", "name": "..."}`)*
- `POST /api/storage/file/create` — Create a new empty file *(payload: `{"path": "...", "name": "..."}`)*
- `POST /api/storage/rename` — Rename a file or folder *(payload: `{"old_path": "...", "new_name": "..."}`)*
- `POST /api/storage/delete` — Delete one or more files or folders *(payload: `{"paths": [...]}`)*
- `POST /api/storage/upload` — Upload files via multipart form data *(form fields: `destination`, `files`)*

### System (`/api/system/*`)
- `GET /api/system/services?scope={user|system|all}` — List systemd services
- `GET /api/system/services/{service_name}?user={bool}` — Get detailed service status
- `GET /api/system/services/{service_name}/logs?lines={n}&user={bool}` — Fetch recent service journal logs
- `POST /api/system/services/{service_name}/{action}?user={bool}` — Run action (`start`, `stop`, `restart`, `enable`, `disable`)
- `GET /api/system/storage` — Get storage usage statistics *(legacy alias for `/api/storage`)*
- `GET /api/system/processes?sort_by={cpu|mem|pid|user|name}&limit={n}` — Get process list and load averages
- `POST /api/system/processes/kill?pid={n}` — Terminate process by PID *(admin required)*
- `GET /api/system/memory` — Get human-readable and raw memory statistics
- `GET /api/system/logs?lines={n}` — Fetch recent system journal entries

### Network & Connectivity (`/api/network/*`)
- `GET /api/network` — Get interface details, WiFi state, DNS servers, gateways, and summary (deprioritizing Tailscale)
- `GET /api/network/ping?target={host}&count={n}` — Perform ping latency test
- `GET /api/network/dns-query?domain={domain}` — Measure DNS lookup latency
- `POST /api/network/wifi-scan` — Trigger scan for nearby wireless networks

### Package Management (`/api/packages/*`)
- `GET /api/packages` — Get installed package count, manager backend, and upgradable packages
- `GET /api/packages/search?query={q}` — Search package repository
- `GET /api/packages/info?package={name}` — Get detailed package information and description
- `POST /api/packages/upgrade` — Upgrade all packages or a specific package *(admin required; optional payload: `{"package": "..."}`)*
- `POST /api/packages/install` — Install a package *(admin required; payload: `{"package": "..."}`)*
- `POST /api/packages/remove` — Remove an installed package *(admin required; payload: `{"package": "..."}`)*

### Power Management & Governors (`/api/power/*`)
- `GET /api/power/state` — Get full power state (battery, thermal, current and available CPU governors, scheduled power actions)
- `POST /api/power/governor` — Set CPU frequency scaling governor across all cores *(admin required; payload: `{"governor": "..."}`)*
- `POST /api/power/schedule` — Schedule a reboot or poweroff in N minutes *(admin required; payload: `{"action": "reboot|poweroff", "minutes": n, "message": "..."}`)*
- `POST /api/power/cancel-scheduled` — Cancel a pending scheduled reboot or poweroff *(admin required)*
- `POST /api/power/reboot` — Reboot device *(admin required)*
- `POST /api/power/poweroff` — Power off device *(admin required)*
- `POST /api/power/suspend` — Suspend device *(admin required)*

### Users, Sessions & SSH (`/api/users/*`)
- `GET /api/users` — Get regular human users, system accounts, group memberships, active sessions, and security posture
- `POST /api/users/session/terminate` — Terminate an active terminal/SSH session *(admin required; payload: `{"tty": "...", "pid": ...}`)*
- `GET /api/users/{username}/ssh-keys` — List SSH public keys in `authorized_keys` for user
- `POST /api/users/{username}/ssh-keys` — Add an SSH public key *(admin required; payload: `{"key": "..."}`)*
- `DELETE /api/users/{username}/ssh-keys/{key_index}` — Delete an SSH public key *(admin required)*
- `POST /api/users/{username}/groups` — Update user group memberships *(admin required; payload: `{"groups": [...]}`)*
- `POST /api/users/{username}/password` — Update user password *(self or admin required; payload: `{"current_password": "...", "new_password": "..."}`)*

### Device Info & Hardware (`/api/device/*`)
- `GET /api/device/info` — Get detected device model, OS distribution, kernel, architecture, and hostname
- `GET /api/device/battery` — Get battery status, thermal zones, and CPU frequencies

### Live Streaming (SSE)
- `GET /api/device/live?metrics=cpu,ram,thermal,battery,network` (or `/api/live`) — Real-time Server-Sent Events stream for subscribed metrics

*(Note: All legacy `/api/device/*` aliases for network, packages, power, and users, and `/api/*` aliases for system endpoints, are fully preserved for backward compatibility).*

---

## Project Structure

```
lavender/
├── server/                      # FastAPI Modular Backend
│   ├── main.py                  # Application entry point, lifespan, routes & SPA fallback
│   ├── config.py                # Re-export of core configuration
│   ├── dependencies.py          # Fast command execution and system utility helpers
│   ├── core/                    # Core infrastructure & configuration
│   │   ├── config.py            # Environment constants, intervals, thresholds, and limits
│   │   ├── executor.py          # Asynchronous subprocess command execution engine
│   │   └── sysfs.py             # Kernel /sys and /proc inspection utilities
│   ├── auth/                    # Linux authentication subsystem
│   │   ├── bridge.py            # PAM, /etc/shadow, and sudo/doas verification engine
│   │   ├── session.py           # In-memory session store with signed cookie serializer
│   │   └── deps.py              # FastAPI auth dependencies (require_session, require_admin)
│   ├── api/                     # Domain REST API routers
│   │   ├── auth.py              # Authentication endpoints (/auth/*)
│   │   ├── device.py            # Hardware specs and battery (/api/device/*)
│   │   ├── system.py            # Services, logs, memory, and processes (/api/system/*)
│   │   ├── storage.py           # Filesystem usage and Web File Browser (/api/storage/*)
│   │   ├── network.py           # Network interfaces, WiFi scanner, ping & DNS (/api/network/*)
│   │   ├── packages.py          # Distro-agnostic package manager (/api/packages/*)
│   │   ├── power.py             # Power actions, CPU governors, schedule (/api/power/*)
│   │   ├── users.py             # User accounts, sessions, SSH keys, groups (/api/users/*)
│   │   └── live.py              # Server-Sent Events (SSE) telemetry (/api/device/live)
│   ├── services/                # Business logic and Linux subsystem integrations
│   │   ├── device_info.py       # Dynamic hardware model, OS, and kernel discovery
│   │   ├── live.py              # SSE MetricCollector, RingBuffer, and telemetry collectors
│   │   ├── systemd.py           # systemctl service status and journalctl log wrappers
│   │   ├── storage.py           # df -h parsing, mount points, and directory usage
│   │   ├── files.py             # File browser service (listing, view, save, raw, upload, delete)
│   │   ├── processes.py         # ps aux and /proc inspection with multi-column sorting
│   │   ├── network.py           # Interfaces, WiFi scanning, DNS info, ping & DNS queries
│   │   ├── battery.py           # sysfs / UPower battery, thermal zones, and CPU frequencies
│   │   ├── packages.py          # Distro-agnostic package managers (apk, apt, pacman, dnf)
│   │   ├── power.py             # Power actions, governor switching, and scheduled timers
│   │   └── users.py             # User accounts, SSH keys, sessions, and security posture
│   ├── schemas/                 # Pydantic v2 validation models
│   ├── utils/                   # System, network, session, and password formatting utilities
│   └── dist/                    # Compiled React SPA production bundle (served at runtime)
│
├── frontend/                    # React 18 + TypeScript SPA Frontend
│   ├── index.html               # Frontend HTML root
│   ├── vite.config.ts           # Vite configuration with proxy to FastAPI backend (:8085)
│   ├── package.json             # Frontend dependencies and scripts
│   └── src/
│       ├── main.tsx             # React application entry point
│       ├── App.tsx              # Router setup, auth gate, and AppShell layout
│       ├── api/                 # API client, TypeScript endpoints, and domain types
│       ├── components/          # Reusable UI components
│       │   ├── common/          # Buttons, modals, badges, spinners, sparklines, error boundaries
│       │   └── layout/          # AppShell, Topbar, Sidebar navigation, UserChip
│       ├── context/             # React Contexts (AuthContext, ToastContext)
│       ├── hooks/               # Custom hooks (useSSE for real-time telemetry)
│       ├── pages/               # Page components
│       │   ├── Overview/        # Telemetry cards, gauges, sparklines, top processes
│       │   ├── Services/        # Systemd service manager and interactive log viewer
│       │   ├── Processes/       # Process monitor with sorting, command copy, and PID kill
│       │   ├── Storage/         # Storage usage and embedded Web File Browser
│       │   ├── Network/         # Interfaces, WiFi scanner, DNS, and latency tools
│       │   ├── Packages/        # Package manager updates, search, details, install/remove
│       │   ├── Users/           # Accounts, active sessions, groups, SSH keys, security audit
│       │   ├── Power/           # Lifecycle actions, CPU governors, scheduled power timers
│       │   └── Login/           # System user sign in page
│       ├── styles/              # Vanilla CSS stylesheets (Lavender theme, responsive, animations)
│       └── utils/               # Formatting and helper utilities
│
├── tests/                       # Backend Automated Test Suite
│   ├── conftest.py              # Pytest fixtures and mock dependencies
│   ├── unit/                    # Unit tests (bridge, executor, live, schemas, session, etc.)
│   └── integration/             # API integration tests (auth, device, network, storage, etc.)
│
├── systemd/
│   └── lavender.service         # systemd user service unit template
├── Makefile                     # Developer command runner (install, dev, build, test)
├── pyproject.toml               # Python package configuration and dependencies
├── requirements.txt             # Core Python runtime dependencies
├── CONTRIBUTING.md              # Contributing guidelines and code standards
├── MIGRATION.md                 # Migration guide for legacy installations
├── LICENSE                      # MIT License
└── README.md                    # Project documentation
```

---

## Testing

Lavender includes comprehensive test suites for both backend and frontend:

```bash
# Run all backend tests (unit & integration tests via pytest)
make test

# Run all frontend tests (components, hooks, utils via Vitest)
make test-frontend

# Run frontend typecheck
cd frontend && bun run typecheck
```

---

## Limitations & Notes

1. **Package Management:** Lavender features a distro-agnostic package adapter framework with support for Alpine / postmarketOS (`apk`), Debian / Ubuntu (`apt`), Arch Linux (`pacman`), and Fedora / RHEL (`dnf`). If an unsupported package manager is present, package management gracefully falls back to a disabled state.
2. **Kernel Sysfs Features:** Certain metrics (such as dynamic CPU frequency scaling or battery power draw) require kernel driver support in `/sys/devices/system/cpu/*/cpufreq` or `/sys/class/power_supply`. On virtual machines or devices without battery or cpufreq drivers, these cards gracefully indicate that the sensor data is unavailable.
3. **Privileged Actions:** Modifying system services, killing processes, installing/upgrading packages, editing user groups/keys, adjusting CPU governors, and triggering power operations require administrative privileges (`wheel` or `sudo` membership) and sudo configured on the host. Root accounts (UID 0) are automatically granted permanent elevation.

---

## Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on development setup, code style, testing, and pull requests.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Credits

Created with ❤️ for postmarketOS on Redmi Note 7 and Linux devices by [rahat](https://github.com/minhazul73).
Powered by FastAPI, Uvicorn, React, TypeScript, and Bun.
