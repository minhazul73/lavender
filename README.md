# RN7 Linux Dashboard

A lightweight FastAPI + HTMX web dashboard for managing postmarketOS on Redmi Note 7 (aarch64). Provides system management, device stats, and Hermes integration through a single-page dark-theme UI.

## Features

- **Systemd Services** — List, start/stop/restart, view logs for user and system services
- **Storage** — Disk usage (df -h), mount points, directory usage (du)
- **Processes** — Top processes by CPU/memory, kill processes, load averages, uptime
- **Network** — IP addresses per interface, WiFi info (iw/iwinfo), DNS servers, ping test
- **Battery** — upower battery info, thermal zones, CPU frequencies, governor info
- **Hermes Controls** — Gateway/dashboard status, restart, logs, version, skills list
- **Packages** — Installed count, upgradable packages, apk upgrade, search
- **Users** — Local users, groups, current user info, sudoers status
- **Power Control** — Reboot, poweroff, suspend with confirmation dialogs
- **Bonus** — Cron jobs, Hermes sessions summary, memory pressure alerts, thermal throttle indicator, network quality ping

## Screenshots

The dashboard uses a dark theme (matching Telegram/device aesthetic) with:
- Fixed sidebar navigation
- Tabbed content areas
- Status indicators (green/red for service states, battery %)
- Confirmation modals for destructive actions
- HTMX-powered dynamic content loading (no page refreshes)

## Quick Start

### Prerequisites

- postmarketOS v26.06 (Alpine-based) or similar Linux
- Python 3.14+ (or 3.11+)
- `uv` for Python package management
- `systemctl --user` for user service management
- `sudo` access for privileged operations

### Installation

```bash
# Clone or navigate to the project
cd /home/rahat/rn7-linux-dashboard

# Install dependencies using uv
uv pip install -r requirements.txt --system

# Or using pip directly (if uv not available)
pip install -r requirements.txt
```

### Running

**Manual run (for testing):**
```bash
cd /home/rahat/rn7-linux-dashboard
python -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080
```

**As a systemd user service (recommended):**
```bash
# Copy the service file to user systemd directory
cp systemd/hermes-device-dashboard.service ~/.config/systemd/user/

# Reload systemd, enable and start
systemctl --user daemon-reload
systemctl --user enable hermes-device-dashboard
systemctl --user start hermes-device-dashboard

# Check status
systemctl --user status hermes-device-dashboard

# View logs
journalctl --user -u hermes-device-dashboard -f
```

### Access

Open http://localhost:8080 in a browser on the device, or from another device on the same network at `http://<device-ip>:8080`.

## Configuration

Edit `dashboard/config.py` to change:
- `PORT` — Dashboard port (default: 8080)
- `HOST` — Bind address (default: 0.0.0.0)
- `THERMAL_WARN_THRESHOLD` — Millidegrees C for thermal warning (default: 70000 = 70°C)
- `MEMORY_PRESSURE_THRESHOLD` — RAM usage fraction for warning (default: 0.85)
- `LOG_LINES` — Lines returned for service logs (default: 50)

## Sudo Requirements

Some actions require sudo:
- **Package upgrade/install** — `sudo apk upgrade`, `sudo apk add`, `sudo apk del`
- **Power actions** — `sudo systemctl reboot/poweroff/suspend`
- **Killing processes** — May need `sudo kill` for processes owned by other users
- **System service management** — `sudo systemctl` for system services

**Setup for passwordless sudo (optional):**

To allow the dashboard to perform sudo actions without prompting, add to `/etc/sudoers.d/hermes-dashboard`:

```
rahat ALL=(ALL) NOPASSWD: /usr/bin/systemctl reboot, /usr/bin/systemctl poweroff, /usr/bin/systemctl suspend, /usr/sbin/apk upgrade, /usr/sbin/apk add, /usr/sbin/apk del, /usr/bin/kill
```

Then:
```bash
sudo visudo -c  # Verify syntax
```

**Note:** This grants passwordless access to specific commands only. The dashboard does NOT currently implement this by default — sudo actions will prompt for a password if NOPASSWD is not configured.

## API Endpoints

All API routes are prefixed with `/api/`:

### System
- `GET /api/system/services` — List services (query: `scope=user|system|all`)
- `GET /api/system/services/{name}` — Service status
- `GET /api/system/services/{name}/logs` — Service logs (query: `lines`, `user`)
- `POST /api/system/services/{name}/{action}` — Start/stop/restart/enable/disable
- `GET /api/system/storage` — Disk usage, mounts, directory usage
- `POST /api/system/storage/unmount?mount_point=X` — Unmount filesystem
- `GET /api/system/processes?sort_by=mem|cpu&limit=N` — Top processes
- `POST /api/system/processes/kill?pid=N` — Kill process
- `GET /api/system/memory` — Memory info

### Hermes
- `GET /api/hermes/status` — Gateway + dashboard status, Hermes info
- `POST /api/hermes/restart-gateway` — Restart gateway
- `POST /api/hermes/restart-dashboard` — Restart dashboard
- `GET /api/hermes/logs?service=gateway|dashboard&lines=N` — Logs
- `GET /api/hermes/cron` — Cron jobs
- `GET /api/hermes/sessions` — Sessions summary
- `GET /api/hermes/memory-pressure` — Memory pressure check
- `GET /api/hermes/network-quality` — Network quality ping

### Device
- `GET /api/device/network` — Interfaces, WiFi, DNS, gateways
- `GET /api/device/network/ping?target=X&count=N` — Ping test
- `GET /api/device/battery` — Battery, thermal, CPU freq
- `GET /api/device/packages` — Installed count, upgradable
- `POST /api/device/packages/upgrade` — Upgrade packages
- `GET /api/device/packages/search?query=X` — Search packages
- `GET /api/device/users` — Users, groups, current user, sudoers
- `POST /api/device/power/reboot` — Reboot
- `POST /api/device/power/poweroff` — Power off
- `POST /api/device/power/suspend` — Suspend

## Limitations & Known Issues

1. **No authentication** — This is a local-device UI. Do NOT expose to LAN without additional security (reverse proxy with auth, firewall rules, etc.).
2. **Sudo password prompts** — Without NOPASSWD sudoers configuration, sudo actions will fail in the web UI (the prompt can't be displayed). Configure passwordless sudo for the specific commands as documented above.
3. **WiFi info** — `iwinfo` is not installed by default on postmarketOS. WiFi info falls back to `iw dev` if available, otherwise shows a note. Install with `sudo apk add iwinfo` for richer data.
4. **CPU frequency** — Some postmarketOS kernels may not expose cpufreq sysfs. If `/sys/devices/system/cpu/cpu*/cpufreq/` is missing, CPU frequency data will show as unavailable.
5. **Service management** — System services require sudo. The UI will attempt sudo commands but may fail if password is required.
6. **Power actions** — Reboot/poweroff/suspend require sudo. Confirm dialogs are shown but the actual action depends on sudo configuration.
7. **HTMX from CDN** — The dashboard loads HTMX from unpkg CDN. For offline use, download `htmxy.min.js` and serve locally from `/static/`.

## Project Structure

```
rn7-linux-dashboard/
├── dashboard/
│   ├── main.py              # FastAPI app, route registration
│   ├── config.py            # Configuration (port, thresholds, paths)
│   ├── dependencies.py      # Shared utilities (run_command, parse_*, etc.)
│   ├── services/
│   │   ├── systemd.py       # systemctl wrappers
│   │   ├── storage.py       # df, mounts, du
│   │   ├── processes.py     # ps, /proc, memory
│   │   ├── network.py       # ip, iw, resolv, ping
│   │   ├── battery.py       # upower, thermal, cpu freq
│   │   ├── packages.py      # apk info/upgrades
│   │   ├── users.py         # passwd/group parse
│   │   └── power.py         # reboot, poweroff, suspend
│   ├── hermes/
│   │   ├── gateway.py       # Gateway/dashboard status, logs, restart, cron, sessions
│   │   └── status.py        # Hermes version, skills
│   ├── api/
│   │   ├── system.py        # /api/system/* routes
│   │   ├── hermes.py        # /api/hermes/* routes
│   │   └── device.py        # /api/device/* routes
│   ├── templates/
│   │   ├── base.html        # Layout, sidebar, HTMX head
│   │   ├── index.html       # Overview dashboard
│   │   ├── services.html    # Systemd services
│   │   ├── storage.html     # Disk/storage
│   │   ├── processes.html   # Process list
│   │   ├── network.html     # Network/WiFi
│   │   ├── battery.html     # Battery/thermal/CPU
│   │   ├── hermes.html      # Hermes controls
│   │   ├── packages.html    # Packages/updates
│   │   ├── users.html       # Users/groups
│   │   └── power.html       # Power control
│   └── static/
│       ├── style.css        # Dark theme CSS (~25KB)
│       └── script.js        # Modal helpers, utilities
├── systemd/
│   └── hermes-device-dashboard.service
├── requirements.txt
└── README.md
```

## Tech Stack

- **Backend:** FastAPI (async, lightweight) + Uvicorn
- **Frontend:** HTMX (progressive enhancement) + Jinja2 templates
- **Styling:** Custom minimal CSS, dark theme, no framework
- **Runtime:** Python 3.14, runs as systemd user service

## Development

### Running tests

Basic smoke test:
```bash
cd /home/rahat/rn7-linux-dashboard
python -c "
import sys
sys.path.insert(0, '.')
from dashboard.main import app
from fastapi.testclient import TestClient
client = TestClient(app)

# Test index
r = client.get('/')
assert r.status_code == 200
assert 'RN7' in r.text

# Test API endpoints
r = client.get('/api/system/services')
assert r.status_code == 200

r = client.get('/api/device/battery')
assert r.status_code == 200

print('All basic tests passed!')
"
```

### Adding new features

1. Add service logic in `dashboard/services/` or `dashboard/hermes/`
2. Add API routes in `dashboard/api/`
3. Add template in `dashboard/templates/`
4. Add navigation link in `base.html`
5. Test manually with `curl` or browser

## License

MIT — see project root for details (not specified, assume permissive).

## Credits

Built for postmarketOS on Redmi Note 7 by rahat.
Powered by FastAPI, HTMX, and Hermes Agent.
