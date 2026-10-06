# Lavender Architecture

## Overview

Lavender is a lightweight, responsive FastAPI web dashboard designed for Linux system management and real-time device monitoring. Built for resource-constrained devices like smartphones running postmarketOS, single-board computers, and home servers, it provides a clean web interface to interact with host system services and resources.

## System Design

```
+-----------------------------------------------------------+
|                        Browser UI                         |
|   (Vanilla JS, SSE Client, Jinja2 Templates, Dark Theme)   |
+-----------------------------+-----------------------------+
                              |
                     HTTP / SSE Stream
                              |
+-----------------------------v-----------------------------+
|                     FastAPI Backend                       |
|  - Auth & Elevation Router (/auth/*)                      |
|  - System API Router (/api/system/*)                      |
|  - Device API Router (/api/device/*)                      |
|  - Live SSE Streaming (/api/device/live)                  |
|  - HTML Page Routes (/, /services, /processes, etc.)      |
+--------------+------------------------------+-------------+
               |                              |
+--------------v---------------+ +------------v-------------+
|    Auth & Security Engine    | |    Service Subsystems    |
| - PAM / Shadow Verification  | | - Systemd (system/user)  |
| - Sudo / Doas Elevation      | | - Disk / Filesystem (df) |
| - Signed Session Cookies     | | - Process Monitor (proc) |
| - Idle Timeout & Purge       | | - Package Manager Adapters|
| - SlowAPI Rate Limiter       | | - Network & WiFi Tools   |
+--------------+---------------+ +------------+-------------+
               |                              |
+--------------v------------------------------v-------------+
|                   Host Linux OS & Kernel                  |
|  - /proc, /sys (sysfs), /dev, /etc/passwd, /etc/group     |
|  - systemctl, journalctl, ip, iw, upower, apk/apt/pacman  |
+-----------------------------------------------------------+
```

## Architectural Layers

### 1. Presentation Layer
- **Jinja2 Templates:** Located in `dashboard/templates/`. Renders server-side HTML.
- **Static Assets:** Located in `dashboard/static/`. Pure vanilla JavaScript (ES6+), CSS custom properties, and icons. No heavy front-end frameworks (React/Vue/Angular) are used, keeping memory footprints negligible.
- **Real-Time Client:** `live.js` connects via Server-Sent Events (`EventSource`) to receive streaming updates for CPU, RAM, thermal, battery, and network without polling overhead.

### 2. Transport & Routing Layer
- **FastAPI Routers:** Modular routers in `dashboard/api/`:
  - `auth.py`: Authentication, logout, and privilege elevation endpoints.
  - `system.py`: Systemd services, disk usage, memory, processes, and journal logs.
  - `device.py`: Hardware specs, network configuration, Wi-Fi scanning, packages, and power controls.
  - `live.py`: Real-time SSE event pipeline.
- **Dependencies & Middlewares:**
  - `get_current_session`: Extracts and validates signed session cookies.
  - `require_session`: Gates protected pages and APIs.
  - `require_admin`: Enforces administrative elevation status.

### 3. Business & Service Layer
- **Encapsulated Services:** Located in `dashboard/services/`. Each module is responsible for a single subsystem:
  - `live.py`: RingBuffer data structures and asynchronous MetricCollectors.
  - `device_info.py`: Dynamic hardware and OS discovery across Device Tree, DMI/SMBIOS, and `/etc/os-release`.
  - `systemd.py`: Wrapper for `systemctl` (system and user sessions) and `journalctl`.
  - `storage.py`: Disk partition parsing (`df -h`) and external mount detection.
  - `processes.py`: Process listing supporting both procps and BusyBox formats.
  - `network.py`: Adapter status, IP address resolution, and Wi-Fi scanning.
  - `battery.py`: UPower and sysfs battery/thermal monitoring.
  - `packages.py`: Multi-distribution package manager abstraction (Alpine `apk`, Debian/Ubuntu `apt`, Arch `pacman`, Fedora `dnf`).
  - `power.py`: System power operations (`reboot`, `poweroff`, `suspend`).
  - `users.py`: User, group, and access control inspection.

### 4. System Interface Layer
- **`dependencies.py` & `dashboard/auth/bridge.py`:**
  - Direct execution of system binaries (`subprocess.run`, `asyncio.create_subprocess_exec`).
  - Native Linux PAM integration via `python-pam`.
  - Elevation management via temporary `sudo -v` tickets.
