# `dashboard/templates/battery.html` — combined fetch (legacy Jinja UI)

**Purpose:** Battery/thermal/CPU-frequency page (now redirects to Overview).

## Key changes

- **Single combined fetch.** All three tabs hit `/api/device/battery`
  separately on every tab switch; now one shared `loadDeviceInfo()` call stores
  the result in `_deviceData` and all tabs / refresh buttons reuse the cache.
  Duplicate `loadThermal()` / `loadCpu()` definitions deleted.

## Performance improvements

- 3 fetches per page load → 1; 1 fetch per tab switch → 0 (cache hit).
- Also deleted 895 lines of stale research docs (`DASHDOT_STUDY.md` etc.).

## Usage

This module is part of the legacy Jinja2 UI, which has since been replaced by
the React SPA. The `battery.html` template no longer exists in the active
codebase but the optimization is preserved in Git history (`21da280`).

## Caveats

- **Legacy code.** This file is no longer part of the live UI. The details
  are primarily for historical context and understanding past optimizations.
- **Redirection.** The route for this page now redirects to the main Overview
  page of the React application.

## Code references

- `dashboard/templates/battery.html` (template since removed in React cutover;
  change preserved in git history at `21da280`)

## Benchmarks

None recorded. See the parent doc
[`docs/optimized-modules.md`](../optimized-modules.md#verification) for how to
produce real numbers.
