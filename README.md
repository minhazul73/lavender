![Lavender Banner](https://github.com/user-attachments/assets/d81858ff-fd52-4931-a35d-6a3e8664a655)

# Lavender

A lightweight, modern web dashboard for Linux system management and real-time device monitoring. Built with a decoupled **FastAPI** modular backend and a sleek **React 18 + TypeScript** Single-Page Application (SPA) frontend.

Originally designed for postmarketOS on ARM64 mobile devices (such as the Redmi Note 7 `lavender`), Lavender features dynamic hardware and OS detection that makes it equally well-suited for single-board computers (Raspberry Pi, Pine64, Orange Pi), Linux phones, laptops, and home servers.

---

## Highlights

- 🔐 **Native Linux PAM & Sudo Elevation** — Sign in with system credentials. Cockpit-style 15-minute temporary elevation with one-click revocation.
- ⚡ **Real-Time Live Telemetry** — Lightweight Server-Sent Events (SSE) streaming CPU frequencies, per-core loads, RAM, multi-zone thermals, battery draw (Watts), and network throughput.
- 📁 **Storage & Web File Manager** — Disk usage gauges combined with an in-browser file browser: view, edit, raw stream media, upload, create, and delete files with safe path traversal defenses.
- 📦 **Distro-Agnostic Package Management** — Native adapters for Alpine/postmarketOS (`apk`), Debian/Ubuntu (`apt`), Arch (`pacman`), and Fedora (`dnf`) with search, update, install, and remove.
- ⚙️ **Systemd Services & Logs** — Control user and system units (`start`, `stop`, `restart`, `enable`, `disable`) with an embedded dark terminal journalctl log viewer.
- 📊 **Interactive Process Explorer** — Real-time process monitor with multi-column sorting, expandable command details with one-click copy, and safe PID termination.
- 🌐 **Network & Diagnostics** — Physical/virtual interface stats (deprioritizing Tailscale), Wi-Fi scanner with signal meters, DNS server detection, and interactive ping/DNS latency tools.
- 📱 **Mobile-First Responsive Design** — Built for mobile Linux phones as well as desktops: dynamic viewport height (`--dvh`), safe area insets (`env(safe-area-inset-*)`), and collapsible navigation.
- 🪶 **Zero Node.js Runtime Overhead** — Single-board computers and embedded devices run Lavender with only Python 3.11+. Pre-compiled production assets are served directly from `server/dist/`.

---

## Tech Stack

- **Backend:** FastAPI (async) · Uvicorn · Pydantic v2 · Python 3.11+ · uv
- **Frontend:** React 18 · TypeScript · Vite · Lucide React · Bun
- **Real-Time:** Server-Sent Events (SSE) via FastAPI `StreamingResponse` & in-memory ring buffers
- **Authentication:** Native Linux PAM (`python-pam`), `/etc/shadow`, `sudo -v` timestamp tickets, signed cookies (`itsdangerous`)
- **Testing:** 140+ automated tests across `pytest` (backend) and `vitest` (frontend)

---

## Quick Start

### Installation

```bash
git clone https://github.com/minhazul73/lavender.git
cd lavender

# With uv (recommended)
uv sync --extra dev

# Or with standard pip
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Running

**Production Server:**
```bash
# Using installed CLI
lavender

# Or via uvicorn
uv run uvicorn server.main:app --host 0.0.0.0 --port 8080
```

**Local Development (with Hot Reload & HMR):**
```bash
make install       # Install backend (uv) and frontend (bun) dependencies
make dev-backend   # Terminal 1: FastAPI on port 8085 with auto-reload
make dev-frontend  # Terminal 2: Vite on port 3000 (proxies API to :8085)
```

Open `http://<device-ip>:8080` (or `http://localhost:3000` during dev) in your web browser.

---

## 📚 Documentation

Detailed guides and references are organized in the [`docs/`](docs/) directory:

| Document | Description |
|:---|:---|
| [📖 **Features Deep Dive**](docs/features.md) | In-depth breakdown of telemetry, file manager, services, packages, and tools |
| [🔌 **API Reference**](docs/api-reference.md) | Complete REST API reference, endpoints, schemas, payloads, and legacy aliases |
| [🏗️ **Architecture & Internals**](docs/architecture.md) | System overview, modular backend, React SPA design, and project directory structure |
| [⚙️ **Configuration Guide**](docs/configuration.md) | Environment variables, thresholds, limits, and SSE collection intervals |
| [🔒 **Authentication & Security**](docs/authentication.md) | Linux PAM, shadow verification, Cockpit-style elevation, and rate limiting |
| [🚀 **Production Deployment**](docs/deployment.md) | Systemd user/system service setup, permissions (`NoNewPrivileges=no`), and reverse proxies |
| [🛠️ **Contributing Guide**](CONTRIBUTING.md) | Development setup, code style standards, and pull request checklist |
| [🔄 **Migration Guide**](MIGRATION.md) | Upgrading existing installations to the modern decoupled architecture |

---

## Testing

```bash
# Backend test suite (61 unit & integration tests)
make test

# Frontend test suite (81 component & hook tests)
make test-frontend

# Frontend TypeScript check
cd frontend && bun run typecheck
```

---

## Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) for code style guidelines and development workflows.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Credits

Created with ❤️ for postmarketOS on Redmi Note 7 and Linux devices by [rahat](https://github.com/minhazul73).
Powered by FastAPI, Uvicorn, React, TypeScript, and Bun.
