# Lavender

A lightweight FastAPI web dashboard for managing postmarketOS on ARM64 devices. Provides system management, device stats, and live monitoring through a dark-theme UI.

## Features

- **Live System Monitoring** — Real-time CPU, RAM, thermal, battery, and network stats via SSE
- **Systemd Services** — List, start/stop/restart, view logs for user and system services
- **Storage** — Disk usage, mount points, directory usage
- **Processes** — Top processes by CPU/memory, kill processes, load averages
- **Network** — IP addresses per interface, WiFi info, DNS servers, ping test
- **Battery** — Battery status, thermal zones, CPU frequency info
- **Packages** — Installed count, upgradable packages, apk upgrade, search
- **Users** — Local users, groups, current user info, sudoers status
- **Power Control** — Reboot, poweroff, suspend with confirmation modals

## Tech Stack

- **Backend:** FastAPI (async) + Uvicorn
- **Frontend:** Jinja2 templates + vanilla JavaScript (no framework)
- **Styling:** Custom minimal CSS, dark theme
- **Real-time:** Server-Sent Events (SSE) for live metrics
- **Runtime:** Python 3.11+, runs as systemd user service

## Quick Start

### Prerequisites

- postmarketOS (Alpine-based) or similar Linux
- Python 3.11+
- `systemctl --user` for user service management
- `sudo` access for privileged operations

### Installation

```bash
git clone https://github.com/minhazul73/lavender.git
cd lavender
pip install -r requirements.txt
```

### Running

**Manual:**
```bash
python -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080
```

**As systemd user service:**
```bash
cp systemd/lavender.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now lavender
```

### Access

Open `http://<device-ip>:8080` in a browser.

## Configuration

Edit `dashboard/config.py` to change:
- `PORT` — Dashboard port (default: 8080)
- `HOST` — Bind address (default: 0.0.0.0)
- `THERMAL_WARN_THRESHOLD` — Thermal warning in millidegrees C (default: 70000 = 70°C)
- `MEMORY_PRESSURE_THRESHOLD` — RAM usage fraction for warning (default: 0.85)
- SSE poll intervals and buffer sizes

## API Endpoints

### System
- `GET /api/system/services` — List services (`scope=user|system|all`)
- `GET /api/system/services/{name}` — Service status
- `GET /api/system/services/{name}/logs` — Service logs (`lines`, `user`)
- `POST /api/system/services/{name}/{action}` — start/stop/restart/enable/disable
- `GET /api/system/storage` — Disk usage, mounts, directory usage
- `GET /api/system/processes` — Top processes (`sort_by=mem|cpu&limit=N`)
- `POST /api/system/processes/kill?pid=N` — Kill process

### Device
- `GET /api/device/network` — Interfaces, WiFi, DNS
- `GET /api/device/network/ping` — Ping test
- `GET /api/device/battery` — Battery, thermal, CPU freq
- `GET /api/device/packages` — Package info
- `POST /api/device/packages/upgrade` — Upgrade packages
- `GET /api/device/users` — Users, groups, sudoers
- `POST /api/device/power/{reboot|poweroff|suspend}` — Power actions

### Live Monitoring (SSE)
- `GET /api/device/live?metrics=cpu,ram,thermal,battery,network` — Real-time metrics stream

## Project Structure

```
lavender/
├── dashboard/
│   ├── main.py              # FastAPI app, route registration
│   ├── config.py            # Configuration (port, thresholds)
│   ├── dependencies.py      # Shared utilities (run_command, etc.)
│   ├── api/
│   │   ├── system.py        # /api/system/* routes
│   │   ├── device.py        # /api/device/* routes
│   │   └── live.py          # SSE live monitoring
│   ├── services/
│   │   ├── systemd.py       # systemctl wrappers
│   │   ├── storage.py       # df, mounts, du
│   │   ├── processes.py     # ps, /proc, memory
│   │   ├── network.py       # ip, iw, resolv, ping
│   │   ├── battery.py       # upower, thermal, cpu freq
│   │   ├── packages.py      # apk info/upgrades
│   │   └── users.py         # passwd/group parse
│   ├── templates/
│   │   ├── base.html        # Layout, sidebar
│   │   ├── index.html       # Live overview dashboard
│   │   ├── services.html    # Systemd services
│   │   ├── storage.html     # Disk/storage
│   │   ├── processes.html   # Process list
│   │   ├── network.html     # Network/WiFi
│   │   ├── battery.html     # Battery/thermal/CPU
│   │   ├── packages.html    # Packages/updates
│   │   ├── users.html       # Users/groups
│   │   └── power.html       # Power control
│   └── static/
│       ├── style.css        # Dark theme CSS
│       ├── script.js        # Modal helpers, utilities
│       ├── live.js          # SSE client, live rendering
│       └── live.css         # Live monitoring styles
├── systemd/
│   └── lavender.service
├── requirements.txt
├── LICENSE
├── CONTRIBUTING.md
└── README.md
```

## Limitations

1. **No authentication** — Local-device UI only. Don't expose without reverse proxy + auth.
2. **Sudo password prompts** — Without NOPASSWD sudoers config, privileged actions will fail silently.
3. **CPU frequency** — Requires kernel with cpufreq sysfs. Some devices may not expose this data.
4. **WiFi info** — `iwinfo` not installed by default on postmarketOS.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE) for details.

## Credits

Built for postmarketOS on Redmi Note 7 by [rahat](https://github.com/minhazul73).
Powered by FastAPI and vanilla JavaScript.
