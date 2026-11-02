# Migration Guide: Upgrading to Lavender SPA Architecture

This guide covers upgrading existing installations of Lavender to the modern architecture featuring a decoupled **FastAPI modular backend** and **React 18 + TypeScript SPA frontend**.

---

## 1. Systemd Service Unit Update

If you run Lavender as a systemd user or system service, the package entry point has changed from `dashboard` to `server`.

### Updating the Unit File

Open your unit file (typically located at `~/.config/systemd/user/lavender.service` or `/etc/systemd/system/lavender.service`):

```diff
 [Unit]
 Description=Lavender Linux System Dashboard
 After=network.target

 [Service]
 Type=simple
 WorkingDirectory=/home/user/lavender
-ExecStart=/home/user/lavender/.venv/bin/uvicorn dashboard.main:app --host 0.0.0.0 --port 8080
+ExecStart=/home/user/lavender/.venv/bin/uvicorn server.main:app --host 0.0.0.0 --port 8080
 Restart=always
 RestartSec=3

 [Install]
 WantedBy=default.target
```

Alternatively, you can use the installed CLI entry point directly:
```ini
ExecStart=/home/user/lavender/.venv/bin/lavender
```

### Reloading systemd

```bash
# For user service
systemctl --user daemon-reload
systemctl --user restart lavender

# For system service
sudo systemctl daemon-reload
sudo systemctl restart lavender
```

---

## 2. Authentication & Session Cookie Update

- The session cookie name has been unified to **`lavender_session`**.
- Upon upgrading, existing sessions will expire cleanly. Users simply log in again with their local Linux account credentials.

---

## 3. Production Deployment on Linux SBCs & Embedded Devices

**Zero Node.js/Bun Runtime Overhead:**
- The production distribution wheel and git releases come with pre-compiled, minified production assets located in `server/dist/`.
- Single-board computers (Raspberry Pi, PinePhone, Orange Pi, Rockchip, Alpine Linux, postmarketOS, Ubuntu/Debian) **do not require Node.js, Bun, or npm installed**.
- Only Python 3.11+ is needed to run the server:

```bash
git pull
.venv/bin/pip install -r requirements.txt
systemctl --user restart lavender
```

---

## 4. API Endpoint Modernization & Compatibility

All backend endpoints are now structured under dedicated domain routers:

| Domain | Modern Route Prefix | Legacy Alias (Preserved) |
|:---|:---|:---|
| **Device Info & Hardware** | `/api/device` | `/api/device` |
| **System & Processes** | `/api/system` | `/api` |
| **Network & WiFi** | `/api/network` | `/api/device/network` |
| **Package Management** | `/api/packages` | `/api/device/packages` |
| **Users & Sessions** | `/api/users` | `/api/device/users` |
| **Power & Governors** | `/api/power` | `/api/device/power` |
| **Storage & File Manager** | `/api/storage` | `/api/storage` (and `/api/system/storage`) |
| **Live Telemetry (SSE)** | `/api/device/live` | `/api/live` |

All legacy endpoint aliases continue to function, ensuring existing curl scripts and automated webhooks will not break. In addition, `/api/storage` now features complete file management endpoints (`/api/storage/files`, `/api/storage/bookmarks`, `/api/storage/file/view`, `/api/storage/file/raw`, `/api/storage/file/save`, `/api/storage/mkdir`, `/api/storage/file/create`, `/api/storage/rename`, `/api/storage/delete`, `/api/storage/upload`).

---

## 5. Local Development Workflow

When developing locally with hot reload:

```bash
# Terminal 1: Backend API server (runs on port 8085 with auto-reload)
make dev-backend

# Terminal 2: Vite dev server with Hot Module Replacement (runs on port 3000, proxies /api and /auth to :8085)
make dev-frontend
```

To compile production assets into `server/dist/` after modifying the frontend:
```bash
make build
```

