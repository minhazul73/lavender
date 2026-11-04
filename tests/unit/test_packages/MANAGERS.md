# Test-to-Manager Mapping (from original tests/unit/test_packages.py)

Source: `tests/unit/test_packages.py` (388 lines, deleted in commit 69f15da, recovered from git history).
All tests imported from `dashboard.services.packages` (now `server.services.packages` after the dashboard→server migration).

## Manager / function mapping

- `BasePackageManager`: test_defaults
- `NullPackageManager`: test_attributes
- `ApkManager`: test_commands, test_get_installed_packages_parses_v_output, test_get_installed_packages_fallback_to_info, test_get_installed_packages_all_fail, test_get_installed_count, test_get_installed_count_fail, test_get_upgradable_packages, test_get_upgradable_packages_fail, test_search_packages, test_search_packages_fail, test_get_package_info
- `AptManager`: test_commands, test_get_installed_packages, test_get_installed_packages_fail, test_get_upgradable_packages, test_get_upgradable_packages_fail, test_search_packages_names_only, test_search_packages_fallback, test_get_package_info_dpkg, test_get_package_info_fallback_apt_cache
- `PacmanManager`: test_commands, test_get_installed_packages, test_get_upgradable_packages, test_get_upgradable_uses_checkupdates, test_search_packages
- `DnfManager`: test_commands, test_get_installed_packages, test_get_upgradable_packages_exit_100, test_get_upgradable_packages_exit_0, test_get_upgradable_packages_error
- `get_package_manager()`: test_detects_apk, test_detects_apt, test_caches_manager
- `Cache & wrappers` (`_PACKAGES_CACHE`, `invalidate_packages_cache`, `get_installed_packages`, `get_installed_count`, `search_packages`, `upgrade_packages`, `install_package`, `remove_package`): test_invalidate_cache, test_get_installed_packages_caching, test_get_installed_packages_force_refresh, test_get_installed_count_from_cache, test_search_packages_empty_query, test_upgrade_packages_no_cmd, test_install_package_success, test_remove_package_failure

## Per-manager file plan (for downstream split)

| File | Manager / scope | Test count |
|---|---|---|
| test_base_classes.py | `BasePackageManager`, `NullPackageManager` | 2 |
| test_apk.py | `ApkManager` | 12 |
| test_apt.py | `AptManager` | 9 |
| test_pacman.py | `PacmanManager` | 5 |
| test_dnf.py | `DnfManager` | 5 |
| test_get_package_manager.py | `get_package_manager()` | 3 |
| test_functions.py | Cache + wrapper functions | 8 |

Total: 44 tests across 7 files.

## Notes for downstream workers
- Import path must be `server.services.packages` (the module was moved from `dashboard.services.packages`).
- `TestCacheAndWrappers.setup_method` and `TestGetPackageManager.setup_method` both reset `pkgs._CURRENT_MANAGER = None` and call `invalidate_packages_cache()` — these belong in a shared `conftest.py` (see task t_098b1898).
- `TestGetPackageManager` and `TestCacheAndWrappers` rely on module-level state (`_CURRENT_MANAGER`, `_PACKAGES_CACHE`), so test ordering matters; a conftest fixture that resets state between tests is recommended.