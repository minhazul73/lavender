# `dashboard/services/packages.py` — package manager adapters

**Purpose:** Distro-agnostic package management (apk / apt / pacman / dnf) —
installed list, upgradable list, search, info, install, remove, upgrade.

## Key changes

- **60-second TTL cache.** In-memory `_PACKAGES_CACHE` (dict with
  `installed` / `timestamp` / `ttl`) for the installed-package listing.
  `get_installed_packages()` returns the cache when fresh;
  `invalidate_packages_cache()` clears it after any install/remove/upgrade so
  mutations never serve stale data.
- **Increased operation timeouts.** Install/remove/upgrade now pass
  `timeout=600` to `run_sudo_async` (was default 30 s), and apt runs with
  unattended options configured so large upgrades no longer time out mid-run.

## Performance improvements

- One `apk`/`dpkg-query`/`pacman`/`rpm` enumeration per 60 s instead of one per
  page load / API hit — reduces host CPU and disk I/O (matters on the RN7, where
  enumerating ~1000+ packages is expensive).
- 600 s timeouts remove false timeouts on slow network package operations
  (reliability rather than raw speed).

## Usage

```python
from dashboard.services.packages import (
    get_installed_packages,
    invalidate_packages_cache,
)

pkgs = get_installed_packages()              # cached, 60 s TTL
pkgs = get_installed_packages(force_refresh=True)  # bypass cache
```

API surface: `GET /api/device/packages`, plus install/remove/upgrade
endpoints, all of which call `invalidate_packages_cache()` after mutating
operations.

## Caveats

- The cache is **per-process in-memory** — a fresh uvicorn worker starts with a
  cold cache (first request pays the enumeration cost).
- **Stale data up to 60 s** is possible for read-only consumers if a package is
  installed outside the dashboard (e.g. `apk add` from a shell). The dashboard
  itself never serves its own mutations stale.
- The 600 s timeout bounds wall time, not CPU: a genuinely stuck package
  operation still occupies one worker for up to 10 minutes.

## Code references

- `dashboard/services/packages.py:15` — `_PACKAGES_CACHE`
- `dashboard/services/packages.py:22` — `invalidate_packages_cache()`
- `dashboard/services/packages.py:621-632` — `get_installed_packages()`
  `get_installed_packages()`

## Tests

- `tests/unit/test_packages/test_cache_and_wrappers.py`

## Benchmarks

None recorded. See the parent doc
[`docs/optimized-modules.md`](../optimized-modules.md#verification) for how to
produce real numbers.
