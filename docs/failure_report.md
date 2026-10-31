# Lavender Failure Report

**Source:** `/tmp/lavender-failures.txt`
**Generated:** 2026-10-31

---

## Status: suite green

No failures are currently outstanding. The full pytest suite reports
**572 passed, 0 failed** (1 deprecation warning from `slowapi`).

---

## Historical failures (for reference)

The pytest cache at `.pytest_cache/v/cache/lastfailed` records **42 tests**
that failed in a prior run. All have since been fixed and currently pass.

### `tests/unit/test_battery_service.py` (7 entries — fixed 2026-10-31)

| Test | Status |
|------|--------|
| `TestGetCpuFrequencies::test_cpu_with_no_freq_files` | Fixed |
| `TestGetCpuFrequencies::test_non_numeric_entries_skipped` | Fixed |
| `TestGetCpuScalingAvailable::test_no_scaling_dir` | Fixed |
| `TestGetCpuScalingAvailable::test_all_scaling_files_present` | Fixed |
| `TestGetCpuScalingAvailable::test_scaling_read_error` | Fixed |
| `TestSetCpuGovernor::test_cpupower_fails_fallback_sysfs` | Fixed |
| `TestSetCpuGovernor::test_all_governor_writes_fail` | Fixed |

The 7 failing tests in `tests/unit/test_battery_service.py`
(`TestGetCpuFrequencies`, `TestGetCpuScalingAvailable`, `TestSetCpuGovernor`)
were caused by a mock misuse: `patch.object(battery.os, "path.isdir", ...)`
sets a literal attribute named `path.isdir` on the `os` module, which does not
exist. `patch.object` does not split dotted attribute names — the correct form
is `patch.object(battery.os.path, "isdir", ...)`.

### `tests/unit/test_packages.py` (12 entries)

| Test | Status |
|------|--------|
| `TestApkManager::test_get_base_command` | Fixed |
| `TestApkManager::test_get_base_command_parametrized[add-expected0]` | Fixed |
| `TestApkManager::test_get_base_command_parametrized[upgrade-expected1]` | Fixed |
| `TestApkManager::test_get_base_command_parametrized[del-expected2]` | Fixed |
| `TestBasePackageManager` | Fixed |
| `TestNullPackageManager` | Fixed |
| `TestApkManager` | Fixed |
| `TestAptManager` | Fixed |
| `TestPacmanManager` | Fixed |
| `TestDnfManager` | Fixed |
| `TestGetPackageManager` | Fixed |
| `TestCacheAndWrappers` | Fixed |

### `tests/unit/test_auth_bridge.py` (12 entries)

| Test | Status |
|------|--------|
| `TestAuthBridge::test_drop_sudo_ticket` | Fixed |
| `TestAuthBridge::test_run_command_async_failure` | Fixed |
| `TestAuthBridge::test_run_command_async_success` | Fixed |
| `TestAuthBridge::test_run_sudo_async_failure` | Fixed |
| `TestAuthBridge::test_run_sudo_async_success` | Fixed |
| `TestAuthBridge::test_run_user_service_async_failure` | Fixed |
| `TestAuthBridge::test_run_user_service_async_success` | Fixed |
| `TestAuthBridge::test_verify_linux_credentials_shadow_failure` | Fixed |
| `TestAuthBridge::test_verify_linux_credentials_shadow_success` | Fixed |
| `TestAuthBridge::test_verify_sudo_password_failure` | Fixed |
| `TestAuthBridge::test_verify_sudo_password_success` | Fixed |

### Remaining historical entries (11)

The other 11 entries in `.pytest_cache/v/cache/lastfailed` span
`tests/test_api.py`, `tests/test_auth.py`, `tests/unit/test_auth_deps.py`,
`tests/unit/test_device_api.py`, `tests/unit/test_device_info_api.py`,
`tests/unit/test_device_power_api.py`, `tests/unit/test_live_api.py`, and
`tests/unit/test_system_api.py`. All have been fixed and currently pass.

---

## Notes

- No stack traces or error snippets were available in the source file.
- The current test suite reports **572 passed, 0 failed**.
- If failure entries are expected, the source file may not have been
  populated correctly by the test runner. Verify the command that
  generates `/tmp/lavender-failures.txt` captures `pytest` stderr/stdout
  with `-v` or `--tb=long`.
