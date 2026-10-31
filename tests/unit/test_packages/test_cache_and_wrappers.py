"""Tests for get_package_manager() detection and cache/wrapper functions."""

from unittest.mock import patch

from dashboard.services import packages as pkgs
from dashboard.services.packages import (
    ApkManager,
    AptManager,
    DnfManager,
    NullPackageManager,
    PacmanManager,
    get_installed_count,
    get_installed_packages,
    get_package_manager,
    get_package_info,
    get_upgradable_packages,
    install_package,
    invalidate_packages_cache,
    remove_package,
    search_packages,
    upgrade_packages,
)


def _reset_cache():
    pkgs._CURRENT_MANAGER = None
    pkgs._PACKAGES_CACHE["installed"] = None
    pkgs._PACKAGES_CACHE["timestamp"] = 0


class TestGetPackageManager:
    def test_detects_apk(self):
        _reset_cache()
        with patch("dashboard.services.packages.shutil.which") as mock_which:
            mock_which.side_effect = lambda p: "/usr/bin/apk" if p == "apk" else None
            mgr = get_package_manager()
        assert isinstance(mgr, ApkManager)

    def test_detects_apt(self):
        _reset_cache()
        with patch("dashboard.services.packages.shutil.which") as mock_which:
            mock_which.side_effect = lambda p: "/usr/bin/apt" if p == "apt" else None
            mgr = get_package_manager()
        assert isinstance(mgr, AptManager)

    def test_detects_pacman(self):
        _reset_cache()
        with patch("dashboard.services.packages.shutil.which") as mock_which:
            mock_which.side_effect = lambda p: (
                "/usr/bin/pacman" if p == "pacman" else None
            )
            mgr = get_package_manager()
        assert isinstance(mgr, PacmanManager)

    def test_detects_dnf(self):
        _reset_cache()
        with patch("dashboard.services.packages.shutil.which") as mock_which:
            mock_which.side_effect = lambda p: "/usr/bin/dnf" if p == "dnf" else None
            mgr = get_package_manager()
        assert isinstance(mgr, DnfManager)

    def test_falls_back_to_null_when_no_pm_found(self):
        _reset_cache()
        with patch("dashboard.services.packages.shutil.which", return_value=None):
            mgr = get_package_manager()
        assert isinstance(mgr, NullPackageManager)

    def test_caches_manager_instance(self):
        _reset_cache()
        with patch("dashboard.services.packages.shutil.which") as mock_which:
            mock_which.side_effect = lambda p: "/usr/bin/dnf" if p == "dnf" else None
            first = get_package_manager()
            count_after_first = mock_which.call_count
            second = get_package_manager()
        assert first is second
        # Cached: second call must not re-run detection
        assert mock_which.call_count == count_after_first


class TestCacheAndWrappers:
    def test_get_installed_packages_uses_cache(self):
        _reset_cache()
        mgr = AptManager()
        mgr.get_installed_packages = lambda: [{"name": "x"}]
        with patch("dashboard.services.packages.get_package_manager", return_value=mgr):
            first = get_installed_packages()
            calls = 0

            def counting():
                nonlocal calls
                calls += 1
                return [{"name": "x"}]

            mgr.get_installed_packages = counting
            second = get_installed_packages()
        assert first == second == [{"name": "x"}]
        assert calls == 0  # served from cache

    def test_get_installed_packages_force_refresh_bypasses_cache(self):
        _reset_cache()
        mgr = AptManager()
        results = [[{"name": "a"}], [{"name": "b"}]]

        def side():
            return results.pop(0)

        mgr.get_installed_packages = side
        with patch("dashboard.services.packages.get_package_manager", return_value=mgr):
            first = get_installed_packages()
            second = get_installed_packages(force_refresh=True)
        assert first == [{"name": "a"}]
        assert second == [{"name": "b"}]

    def test_get_installed_count_from_cache(self):
        # When the cache is populated, count reads from it, not the manager
        pkgs._PACKAGES_CACHE["installed"] = [{}, {}, {}]
        assert get_installed_count() == 3

    def test_get_installed_count_queries_manager_when_cache_cold(self):
        _reset_cache()
        mgr = AptManager()
        mgr.get_installed_count = lambda: 42
        with patch("dashboard.services.packages.get_package_manager", return_value=mgr):
            assert get_installed_count() == 42

    def test_get_upgradable_packages_delegates(self):
        _reset_cache()
        mgr = AptManager()
        mgr.get_upgradable_packages = lambda: [{"name": "x"}]
        with patch("dashboard.services.packages.get_package_manager", return_value=mgr):
            result = get_upgradable_packages()
        assert result == [{"name": "x"}]

    def test_search_packages_empty_query(self):
        _reset_cache()
        assert search_packages("   ") == []

    def test_search_packages_delegates(self):
        _reset_cache()
        mgr = AptManager()
        mgr.search_packages = lambda q: [{"name": q}]
        with patch("dashboard.services.packages.get_package_manager", return_value=mgr):
            result = search_packages("htop")
        assert result == [{"name": "htop"}]

    def test_get_package_info_delegates(self):
        _reset_cache()
        mgr = AptManager()
        mgr.get_package_info = lambda name: {"package": name}
        with patch("dashboard.services.packages.get_package_manager", return_value=mgr):
            result = get_package_info("htop")
        assert result == {"package": "htop"}

    def test_upgrade_packages_runs_sudo(self):
        _reset_cache()
        mgr = AptManager()
        with patch(
            "dashboard.services.packages.get_package_manager", return_value=mgr
        ), patch(
            "dashboard.services.packages.run_sudo_command", return_value=(0, "OK", "")
        ) as mock_sudo:
            result = upgrade_packages()
        assert result["success"] is True
        assert mock_sudo.call_args[0][0][:3] == ["apt-get", "upgrade", "-y"]
        assert pkgs._PACKAGES_CACHE["installed"] is None  # cache invalidated

    def test_upgrade_packages_with_specific_package(self):
        _reset_cache()
        mgr = AptManager()
        with patch(
            "dashboard.services.packages.get_package_manager", return_value=mgr
        ), patch(
            "dashboard.services.packages.run_sudo_command", return_value=(0, "OK", "")
        ) as mock_sudo:
            upgrade_packages("htop")
        assert "htop" in mock_sudo.call_args[0][0]

    def test_install_package_runs_sudo(self):
        _reset_cache()
        mgr = AptManager()
        with patch(
            "dashboard.services.packages.get_package_manager", return_value=mgr
        ), patch(
            "dashboard.services.packages.run_sudo_command", return_value=(0, "OK", "")
        ) as mock_sudo:
            result = install_package("htop")
        assert result["success"] is True
        assert "htop" in mock_sudo.call_args[0][0]

    def test_remove_package_runs_sudo(self):
        _reset_cache()
        mgr = AptManager()
        with patch(
            "dashboard.services.packages.get_package_manager", return_value=mgr
        ), patch(
            "dashboard.services.packages.run_sudo_command", return_value=(0, "OK", "")
        ) as mock_sudo:
            result = remove_package("htop")
        assert result["success"] is True
        assert "htop" in mock_sudo.call_args[0][0]

    def test_upgrade_failure_reports_error(self):
        _reset_cache()
        mgr = AptManager()
        with patch(
            "dashboard.services.packages.get_package_manager", return_value=mgr
        ), patch(
            "dashboard.services.packages.run_sudo_command",
            return_value=(100, "", "no such pkg"),
        ):
            result = upgrade_packages("htop")
        assert result["success"] is False
        assert result["error"] == "no such pkg"

    def test_invalidate_packages_cache_clears(self):
        pkgs._PACKAGES_CACHE["installed"] = [{"name": "x"}]
        pkgs._PACKAGES_CACHE["timestamp"] = 12345
        invalidate_packages_cache()
        assert pkgs._PACKAGES_CACHE["installed"] is None
        assert pkgs._PACKAGES_CACHE["timestamp"] == 0
