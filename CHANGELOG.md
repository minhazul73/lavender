# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]
### Security
- Eliminated subprocess sink in command executor and replaced with strict executable allowlist
- Resolved CodeQL alerts for path traversal in storage file preview, raw streaming, and upload endpoints
- Added strict destination sanitization for open redirect protection in `/auth/login`, `/auth/logout`, and SPA fallback routing
- Hardened input validation for package names, ping targets, and DNS resolution hostnames

### Changed
- Removed obsolete `server/dependencies.py` and `server/config.py` shims in favor of direct modular imports
- Split monolithic styles into domain stylesheets (`live.css`, `components.css`, `tables.css`, `forms.css`, `modals.css`, `file-browser.css`, `animations.css`)
- Extracted modular power components (`PowerActionsCard`, `CpuGovernorCard`, `ScheduledPowerCard`) from `PowerPage`

### Performance
- Added `React.lazy()` route-based code splitting for dashboard page bundles
- Audited and deduplicated CSS declarations in `live.css`

### Reliability & UX
- Added per-page React Error Boundaries to prevent full dashboard crashes from component errors
- Enhanced native system font fallbacks (`system-ui`, `ui-monospace`) for resilient air-gapped deployments

### CI & Tooling
- Added non-blocking Ruff lint step to backend CI workflow
- Added ESLint lint step to frontend CI workflow

### Dependencies
- Bumped `certifi` from 2026.7.22 to 2026.10.18

## [0.5.0] — 2026-11-02
### Added
- Full React SPA migration (Phase 4 cutover from Jinja2)
- Real-time SSE telemetry (CPU, RAM, thermal, battery, network)
- File manager with preview, edit, create, rename, delete, upload
- Package management for apk/apt/pacman/dnf
- User & group administration with SSH key management
- Power management (CPU governor, scheduled shutdown)
- Process monitor with kill support
- systemd service control with journal log viewer
- Network dashboard with WiFi scanner, DNS query, ping tool
- Dynamic runtime and build-time version synchronization across frontend and backend

[Unreleased]: https://github.com/minhazul73/lavender/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/minhazul73/lavender/releases/tag/v0.5.0

