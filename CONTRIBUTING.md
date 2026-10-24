# Contributing to Lavender

Thank you for your interest in contributing to Lavender! This document outlines how to set up your development environment, our architectural standards, code style, and how to submit contributions.

---

## Architecture Overview

Lavender uses a modern, decoupled architecture:
- **Backend (`server/`):** Asynchronous FastAPI application running on Python 3.11+, structured with modular routers, Pydantic v2 schemas, and Linux system services. Managed with `uv`.
- **Frontend (`frontend/`):** React 18 Single-Page Application (SPA) with TypeScript and Vite, built using custom responsive CSS and Lucide React icons. Managed with `bun` (or `npm`).
- **Production Asset Distribution:** The compiled React SPA resides in `server/dist/`. On target Linux SBCs and mobile devices (postmarketOS, Raspberry Pi, etc.), Lavender runs as a standalone Python package with **zero Node.js or Bun runtime dependency**.

---

## Development Prerequisites

- **Linux operating system** (or Linux VM / WSL2 with system access)
- **Python 3.11+**
- **uv** (recommended: `curl -LsSf https://astral.sh/uv/install.sh | sh`) or standard Python `venv`
- **bun** (recommended: `curl -fsSL https://bun.sh/install | bash`) or Node.js 18+ with `npm`
- **Linux PAM development headers** (e.g., `linux-pam-dev` on Alpine/postmarketOS, `libpam0g-dev` on Debian/Ubuntu)

---

## Development Setup

The easiest way to get started is using the provided `Makefile`:

```bash
# 1. Clone the repository
git clone https://github.com/minhazul73/lavender.git
cd lavender

# 2. Install backend dependencies (uv) and frontend dependencies (bun)
make install
```

### Running the Local Development Environment

Lavender runs the backend API server and the frontend Vite HMR server side-by-side during development:

```bash
# Terminal 1: Launch FastAPI backend on port 8085 with auto-reload
make dev-backend

# Terminal 2: Launch Vite frontend development server on port 3000 (proxies API to :8085)
make dev-frontend
```

Open `http://localhost:3000` in your browser. Changes in `frontend/src/` will hot-reload immediately via Vite HMR.

---

## Code Style & Architecture Guidelines

### Backend (`server/`)
- **Python Version:** Python 3.11+
- **Style:** Follow PEP 8 guidelines. Use explicit type hints for all function arguments and return types.
- **Modularity:**
  - Place domain API routes in `server/api/<domain>.py`.
  - Place business logic, OS/sysfs interactions, and command runners in `server/services/<domain>.py`.
  - Place request/response validation models in `server/schemas/<domain>.py`.
  - Use `server.core.executor.run_command` or async subprocesses rather than blocking synchronous I/O.
- **Error Handling:** Return structured `HTTPException` responses with user-friendly error details.

### Frontend (`frontend/src/`)
- **Framework & Language:** React 18 with TypeScript. Always maintain strict type safety (`npm run typecheck` / `bun run typecheck`).
- **Icons:** Use `lucide-react` icons. Keep icon sizes consistent (`size={16}` for inline actions, `size={18}`–`20` for nav/card titles).
- **Styling:** Custom Vanilla CSS with CSS custom properties (`var(--lavender-*)`, `var(--bg-base)`, etc.). Avoid adding CSS-in-JS or heavy UI utility libraries like Tailwind CSS.
- **Responsiveness & Mobile-First:** Use dynamic viewport units (`--dvh`), safe area insets (`env(safe-area-inset-*)`), and flexible flex/grid layouts so the dashboard looks beautiful on small screens (e.g. postmarketOS on mobile phones) as well as desktop monitors.

---

## Testing

Always verify that tests pass before opening a pull request:

```bash
# Run backend pytest suite (unit & integration tests)
make test

# Run frontend Vitest suite
make test-frontend

# Verify frontend TypeScript types
cd frontend && bun run typecheck
```

---

## Building Production Assets

Whenever you make changes to the frontend that should be included in releases:

```bash
# Compiles and minifies the React SPA into server/dist/
make build
```

---

## Pull Request Guidelines

1. **Keep PRs Focused:** Create atomic, well-described PRs for specific bug fixes or features.
2. **Include Tests:** Add unit tests in `tests/` for backend changes and in `frontend/src/**/*.test.tsx` for frontend components.
3. **Hardware Compatibility:** Keep ARM64, postmarketOS, and low-resource devices (≤3 GB RAM) in mind. Avoid CPU-heavy client computations and unbuffered telemetry streams.
4. **Preserve API Compatibility:** Ensure any new endpoints include backward-compatibility aliases if replacing legacy routes.
5. **Update Documentation:** Update `README.md` and related docs if adding or modifying API endpoints, configuration variables, or user-facing features.

---

## Code of Conduct

Be welcoming, respectful, and constructive. This project is built for the open-source Linux community.

