# `dashboard/auth/bridge.py` — async subprocess execution

**Purpose:** Native Linux credential verification (shadow → PAM → sudo → doas)
and the async command-execution engine used across all privileged endpoints.

## Key changes

- **Timeout handling.** `run_command_async` / `run_sudo_async` /
  `run_user_service_async` now catch both `asyncio.TimeoutError` and builtin
  `TimeoutError`, and on timeout or any exception they `proc.kill()` **and**
  `await proc.wait()` — previously a timed-out child was killed without reaping,
  leaking zombie processes on repeated timeouts.
- **`TimeoutError` alias.** Switched to builtin `TimeoutError` (3.11+ alias of
  `asyncio.TimeoutExpired`) to avoid import-ordering issues.

## Performance improvements

- No process leak under timeout conditions (zombies accumulate otherwise and
  consume PIDs/memory over long uptime — critical for an always-on dashboard on
  a phone).

## Usage

These functions are used internally by other service modules requiring
privileged execution or subprocess management. For example:

```python
from dashboard.auth.bridge import run_sudo_async

code, out, err = await run_sudo_async(["apt", "update"]) # runs with sudo
```

Directly exposed in the API via endpoints like `/api/packages/install`.

## Caveats

- **Privilege escalation.** These functions run commands with elevated
  privileges (e.g., `sudo`). Misuse can lead to security vulnerabilities. All
  API calls should validate user input thoroughly before passing to these.
- **Zombie processes.** While the fix prevents leaking *timed-out* zombies,
  other abnormal exits (e.g., `SIGKILL` by an external agent) could still
  leave zombies if not explicitly `wait()`ed on elsewhere.
- **Timeout behavior.** Commands that hang indefinitely, even after `kill()`,
  will still hold a task open until `await proc.wait()` eventually resolves
  or the parent task itself times out. (This is a low-level OS behavior)

## Code references

- `dashboard/auth/bridge.py:175` — `run_command_async()`
- `dashboard/auth/bridge.py:205` — `run_user_service_async()`
- `dashboard/auth/bridge.py:263` — `run_sudo_async()`

## Tests

- `tests/unit/test_auth_deps.py`
- `tests/test_auth.py`

## Benchmarks

None recorded. See the parent doc
[`docs/optimized-modules.md`](../optimized-modules.md#verification) for how to
produce real numbers.
