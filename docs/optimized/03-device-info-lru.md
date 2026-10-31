# `dashboard/services/device_info.py` — hardware/OS discovery

**Purpose:** Detects device model, OS distro, kernel, arch, hostname via a
6-level fallback chain (devicetree → `/etc/deviceinfo` → DMI → `hostnamectl`
→ `/etc/machine-info` → `socket.gethostname()`).

## Key changes

- Result is memoized with `@lru_cache(maxsize=1)` at
  `dashboard/services/device_info.py:156` on `get_system_info()`, because
  hardware and OS identity do not change at runtime.

## Performance improvements

- The full probe chain (several file reads + up to a `hostnamectl` subprocess)
  runs exactly once per process lifetime; every subsequent
  `GET /api/device/info` returns from memory.

## Usage

```python
from dashboard.services.device_info import get_system_info

info = get_system_info()  # first call: full probe chain; later: cache hit
```

## Caveats

- `lru_cache` is **per-process**: each uvicorn worker pays the probe cost once
  (cheap, but relevant if you scale workers on the RN7).
- If the result is ever needed fresh (e.g. in tests), call
  `get_system_info.cache_clear()` — otherwise a stale value persists for the
  whole process lifetime.
- The 6-level fallback means different devices report model strings from
  different sources; UI code should treat `model` as opaque display text, not
  an enum.

## Code references

- `dashboard/services/device_info.py:156` — `@lru_cache(maxsize=1)` on
  `get_system_info()`

## Tests

- `tests/unit/test_device_info_services.py`

## Benchmarks

None recorded. See the parent doc
[`docs/optimized-modules.md`](../optimized-modules.md#verification) for how to
produce real numbers.
