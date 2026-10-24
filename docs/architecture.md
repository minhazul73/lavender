# Architecture & Internals

Lavender is engineered with a clean, decoupled design: a high-performance asynchronous **FastAPI** backend paired with a modern, responsive **React 18 + TypeScript** Single-Page Application (SPA).

---

## 1. System Overview

```
┌────────────────────────────────────────────────────────┐
│               Client Web Browser / Mobile              │
│       React 18 SPA (React Router, Custom CSS)          │
└───────────────▲────────────────────────▲───────────────┘
                │ HTTP Requests          │ Server-Sent Events (SSE)
                │ (/api/*, /auth/*)      │ (/api/device/live)
┌───────────────▼────────────────────────┴───────────────┐
│                 FastAPI Modular Backend                │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Middleware: Session Resolver, Cache-Control, Hosts │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ Domain Routers: Auth, Storage, System, Network...  │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ Auth Bridge: PAM, /etc/shadow, Sudo/Doas Elevation │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ Async Executor & Sysfs/Procfs Query Engine         │ │
│ └────────────────────────────────────────────────────┘ │
└───────────────────────────▲────────────────────────────┘
                            │ Kernel & System Calls
┌───────────────────────────▼────────────────────────────┐
│                    Host Linux OS                       │
│  /proc, /sys, systemd, PAM, package manager (apk/apt)  │
└────────────────────────────────────────────────────────┘
```

---

## 2. Asynchronous Backend Architecture (`server/`)

- **Domain-Driven Modular Routers (`server/api/`):**
  Each functional area (auth, device, storage, network, packages, power, system, users, live) has its own dedicated router file.
- **Service Isolation (`server/services/`):**
  Business logic and operating system wrappers reside in `server/services/`. API routers remain thin controllers that validate schemas and dispatch to services.
- **Non-Blocking Subprocess Execution (`server/core/executor.py`):**
  Command execution uses `asyncio.create_subprocess_exec` with timeouts to prevent hanging processes and UI blocking.
- **SSE Telemetry Pipeline (`server/services/live.py`):**
  Uses rolling in-memory `RingBuffer` queues to retain historical metrics for sparklines without database overhead or disk writes.

---

## 3. Frontend Architecture (`frontend/`)

- **React 18 + TypeScript:** Strict compile-time type safety with centralized domain types in `frontend/src/api/types.ts`.
- **Vite & Bun:** High-speed development environment with Hot Module Replacement (HMR) and lightweight dependency management.
- **Vanilla CSS Design System:**
  - Tokenized color variables (`variables.css`, `base.css`).
  - Dark theme with glassmorphic cards and accent glow effects (`live.css`, `components.css`).
  - Mobile-first responsiveness using dynamic viewport height (`--dvh`) and safe area insets (`env(safe-area-inset-*)`).
- **State & Contexts:**
  - `AuthContext`: Tracks session state, local user information, elevation tickets, and login/logout handlers.
  - `ToastContext`: System-wide notification toasts.
  - `useSSE` Hook: Robust EventSource subscription with auto-reconnection and metric ring buffers.

---

## 4. Zero Node Runtime Distribution

For single-board computers (Raspberry Pi, PinePhone, Rockchip, Alpine Linux, etc.), installing Node.js or Bun adds unnecessary RAM and storage overhead.

- During the release process, the frontend is compiled into static, minified HTML/JS/CSS assets inside [`server/dist/`](file:///home/rahat/Documents/vscode/FASTAPI/lavender/server/dist/).
- On target production devices, FastAPI mounts and serves `server/dist/` directly.
- **Result:** Only Python 3.11+ is needed to run Lavender in production.

---

## 5. Detailed Project Structure

```
lavender/
├── server/                      # FastAPI Modular Backend
│   ├── main.py                  # Entrypoint, middleware, routes, and SPA fallback
│   ├── config.py                # Re-export of core configuration
│   ├── dependencies.py          # Command runners and system utility helpers
│   ├── core/                    # Core configuration, executor, and sysfs helpers
│   ├── auth/                    # Linux PAM, shadow, session store, elevation
│   ├── api/                     # Domain REST API routers (auth, storage, network...)
│   ├── services/                # Linux integrations (systemd, packages, files, power...)
│   ├── schemas/                 # Pydantic v2 validation models
│   ├── utils/                   # System, network, formatting helpers
│   └── dist/                    # Compiled React SPA production bundle
│
├── frontend/                    # React 18 + TypeScript SPA Frontend
│   ├── index.html               # Frontend HTML root
│   ├── vite.config.ts           # Vite config with proxy to backend (:8085)
│   ├── package.json             # Frontend dependencies and scripts
│   └── src/
│       ├── main.tsx             # Application bootstrap
│       ├── App.tsx              # Routing, auth gate, layout shell
│       ├── api/                 # API client & TypeScript interfaces
│       ├── components/          # Reusable UI components & layouts
│       ├── context/             # AuthContext, ToastContext
│       ├── hooks/               # useSSE telemetry hook
│       ├── pages/               # Page views (Overview, Storage, Services, etc.)
│       ├── styles/              # Design system stylesheets
│       └── utils/               # Formatters and test utilities
│
├── docs/                        # Project documentation
│   ├── api-reference.md         # Complete REST API reference
│   ├── architecture.md          # Architecture and internal design
│   ├── authentication.md        # PAM, shadow, elevation, and security
│   ├── configuration.md         # Environment variables and thresholds
│   ├── deployment.md            # Systemd and production deployment
│   └── features.md              # Detailed breakdown of features
│
├── tests/                       # Automated backend tests (pytest)
├── systemd/                     # Systemd service unit template
├── Makefile                     # Developer command runner (install, dev, test, build)
├── pyproject.toml               # Python package configuration
├── requirements.txt             # Core Python runtime dependencies
├── CONTRIBUTING.md              # Contribution standards and guidelines
├── MIGRATION.md                 # Migration guide for legacy upgrades
├── LICENSE                      # MIT License
└── README.md                    # Project overview and quick start
```
