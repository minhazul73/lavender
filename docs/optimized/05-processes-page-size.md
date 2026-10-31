# `dashboard/services/processes.py` — process monitor

**Purpose:** Process listing (procps + BusyBox `ps` formats), load averages,
kill-by-PID.

## Key changes

- **Page-size RSS.** RSS/VSZ for BusyBox processes are read from
  `/proc/<pid>/stat` and multiplied by the actual system page size instead of
  assuming 4 KiB — correct memory figures on any `PAGE_SIZE`.
- **Load-average aliases.** Load-average dict expanded with alias keys
  (`1m`/`5m`/`15m`, `load1`/`load5`/`load15`) so frontend consumers need no
  key-mapping.
- **BusyBox fallback.** 4-column `ps aux` fallback with per-PID
  `/proc/<pid>/stat` inspection for RSS/VSZ/memory %.

## Performance improvements

- Single `ps` invocation per request; per-process stat reads only happen for
  the BusyBox fallback path. Alias keys remove repeated key-lookup fallbacks on
  the client side.

## Usage

```python
from dashboard.services.processes import get_processes, get_system_load

procs = get_processes(sort="mem", limit=20)
load = get_system_load()  # includes aliases: "1m", "5m", "15m", "load1", ...
```

Exposed via `GET /api/processes` and the load widget on the Overview page.

## Caveats

- On the BusyBox path, one `/proc/<pid>/stat` read is done **per process**, so
  a very large process table makes that request linear in PID count. The procps
  path avoids this entirely.
- RSS/VSZ for a process that exits between `ps` and the stat read fall back to
  zero/unknown for that row.
- Load-average aliases are additive; both `1m` and `load1` are present in the
  response, so clients pick one convention rather than mapping keys.

## Code references

- `dashboard/services/processes.py:148` — `get_system_load()`

## Tests

- `tests/unit/test_processes.py`

## Benchmarks

None recorded. See the parent doc
[`docs/optimized-modules.md`](../optimized-modules.md#verification) for how to
produce real numbers.
