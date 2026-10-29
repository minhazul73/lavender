"""Unit tests for dashboard.services.packages."""

import time
from unittest.mock import patch, MagicMock

import pytest

from dashboard.services.packages import (
    BasePackageManager,
    ApkManager,
    AptManager,
    PacmanManager,
    DnfManager,
    NullPackageManager,
    get_package_manager,
    invalidate_packages_cache,
    get_installed_packages,
    get_installed_count,
    get_upgradable_packages,
    search_packages,
    get_package_info,
    upgrade_packages,
    install_package,
    remove_package,
    _PACKAGES_CACHE,
)


class TestBasePackageManager:
    def test_defaults(self):
        mgr = BasePackageManager()
        assert mgr.id == "generic"
        assert mgr.is_available() is False
        assert mgr.get_installed_packages() == []
        assert mgr.get_installed_count() == 0
        assert mgr.get_upgradable_packages() == []
        assert mgr.search_packages("x") == []
        assert mgr.get_package_info("x")["package"] == "x"
        assert mgr.get_upgrade_command() == []
        assert mgr.get_install_command("x") == []
        assert mgr.get_remove_command("x") == []


class TestNullPackageManager:
    def test_attributes(self):
        mgr = NullPackageManager()
        assert mgr.id == "none"
        assert mgr.is_available() is False


class TestApkManager:
    def test_commands(self):
        mgr = ApkManager()
        assert mgr.get_install_command("htop") == ["apk", "add", "htop"]
        assert mgr.get_remove_command("htop") == ["apk", "del", "htop"]
        assert mgr.get_upgrade_command() == ["apk", "upgrade"]
        assert mgr.get_upgrade_command("htop") == ["apk", "add", "-u", "htop"]

    @patch("dashboard.services.packages.run_command")
    def test_get_installed_packages_parses_v_output(self, mock_run):
        mock_run.return_value = (0, "musl-1.2.4-r0\nbusybox-1.36.1-r2\n", "")
        pkgs = ApkManager().get_installed_packages()
        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "busybox"
        assert pkgs[0]["version"] == "1.36.1-r2"
        assert pkgs[1]["name"] == "musl"

    @patch("dashboard.services.packages.run_command")
    def test_get_installed_packages_fallback_to_info(self, mock_run):
        mock_run.side_effect = [
            (1, "", "err"),
            (0, "musl\nbusybox\n", ""),
        ]
        pkgs = ApkManager().get_installed_packages()
        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "busybox"
        assert pkgs[0]["version"] == ""

    @patch("dashboard.services.packages.run_command")
    def test_get_installed_packages_all_fail(self, mock_run):
        mock_run.return_value = (1, "", "err")
        assert ApkManager().get_installed_packages() == []

    @patch("dashboard.services.packages.run_command")
    def test_get_installed_count(self, mock_run):
        mock_run.return_value = (0, "a\nb\nc\n", "")
        assert ApkManager().get_installed_count() == 3

    @patch("dashboard.services.packages.run_command")
    def test_get_installed_count_fail(self, mock_run):
        mock_run.return_value = (1, "", "err")
        assert ApkManager().get_installed_count() == 0

    @patch("dashboard.services.packages.run_command")
    def test_get_upgradable_packages(self, mock_run):
        mock_run.return_value = (
            0,
            "busybox-1.36.1-r3 aarch64 {busybox} [upgradable from: busybox-1.36.1-r2]\n",
            "",
        )
        pkgs = ApkManager().get_upgradable_packages()
        assert len(pkgs) == 1
        assert pkgs[0]["current_version"] == "busybox-1.36.1-r2"

    @patch("dashboard.services.packages.run_command")
    def test_get_upgradable_packages_fail(self, mock_run):
        mock_run.return_value = (1, "", "network error")
        pkgs = ApkManager().get_upgradable_packages()
        assert pkgs[0]["error"] == "network error"

    @patch("dashboard.services.packages.run_command")
    def test_search_packages(self, mock_run):
        mock_run.return_value = (0, "htop-3.3.0-r0\n", "")
        results = ApkManager().search_packages("htop")
        assert len(results) == 1
        assert results[0]["name"] == "htop"

    @patch("dashboard.services.packages.run_command")
    def test_search_packages_fail(self, mock_run):
        mock_run.return_value = (1, "", "err")
        results = ApkManager().search_packages("htop")
        assert results[0]["error"] == "err"

    @patch("dashboard.services.packages.run_command")
    def test_get_package_info(self, mock_run):
        mock_run.return_value = (0, "htop description", "")
        info = ApkManager().get_package_info("htop")
        assert info["info"] == "htop description"
        assert info["error"] is None


class TestAptManager:
    def test_commands(self):
        mgr = AptManager()
        assert mgr.get_install_command("htop") == ["apt-get", "install", "-y", "htop"]
        assert mgr.get_remove_command("htop") == ["apt-get", "remove", "-y", "htop"]
        assert mgr.get_upgrade_command() == ["apt-get", "upgrade", "-y"]
        assert mgr.get_upgrade_command("htop") == [
            "apt-get",
            "install",
            "--only-upgrade",
            "-y",
            "htop",
        ]

    @patch("dashboard.services.packages.run_command")
    def test_get_installed_packages(self, mock_run):
        mock_run.return_value = (0, "htop\t3.3.0\tamd64\nvim\t9.0\tamd64\n", "")
        pkgs = AptManager().get_installed_packages()
        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "htop"
        assert pkgs[0]["arch"] == "amd64"

    @patch("dashboard.services.packages.run_command")
    def test_get_installed_packages_fail(self, mock_run):
        mock_run.return_value = (1, "", "err")
        assert AptManager().get_installed_packages() == []

    @patch("dashboard.services.packages.run_command")
    def test_get_upgradable_packages(self, mock_run):
        line = "htop/jammy-updates 3.3.0-1 amd64 [upgradable from: 3.2.0-1]"
        mock_run.return_value = (0, f"Listing...\n{line}\n", "")
        pkgs = AptManager().get_upgradable_packages()
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "htop"
        assert pkgs[0]["current_version"] == "3.2.0-1"

    @patch("dashboard.services.packages.run_command")
    def test_get_upgradable_packages_fail(self, mock_run):
        mock_run.return_value = (1, "", "err")
        pkgs = AptManager().get_upgradable_packages()
        assert "error" in pkgs[0]

    @patch("dashboard.services.packages.run_command")
    def test_search_packages_names_only(self, mock_run):
        mock_run.return_value = (0, "htop - interactive process viewer\n", "")
        results = AptManager().search_packages("htop")
        assert results[0]["name"] == "htop"
        assert "interactive" in results[0]["description"]

    @patch("dashboard.services.packages.run_command")
    def test_search_packages_fallback(self, mock_run):
        mock_run.side_effect = [
            (0, "", ""),
            (0, "htop - interactive process viewer\n", ""),
        ]
        results = AptManager().search_packages("htop")
        assert len(results) == 1

    @patch("dashboard.services.packages.run_command")
    def test_get_package_info_dpkg(self, mock_run):
        mock_run.return_value = (0, "Package: htop\nVersion: 3.3.0\n", "")
        info = AptManager().get_package_info("htop")
        assert "htop" in info["info"]

    @patch("dashboard.services.packages.run_command")
    def test_get_package_info_fallback_apt_cache(self, mock_run):
        mock_run.side_effect = [
            (1, "", "not installed"),
            (0, "Package: htop\n", ""),
        ]
        info = AptManager().get_package_info("htop")
        assert "htop" in info["info"]


class TestPacmanManager:
    def test_commands(self):
        mgr = PacmanManager()
        assert mgr.get_install_command("htop") == [
            "pacman",
            "-S",
            "--noconfirm",
            "htop",
        ]
        assert mgr.get_remove_command("htop") == ["pacman", "-R", "--noconfirm", "htop"]
        assert mgr.get_upgrade_command() == ["pacman", "-Syu", "--noconfirm"]

    @patch("dashboard.services.packages.run_command")
    def test_get_installed_packages(self, mock_run):
        mock_run.return_value = (0, "htop 3.3.0-1\nvim 9.0-1\n", "")
        pkgs = PacmanManager().get_installed_packages()
        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "htop"
        assert pkgs[0]["version"] == "3.3.0-1"

    @patch("dashboard.services.packages.run_command")
    def test_get_upgradable_packages(self, mock_run):
        mock_run.return_value = (0, "htop 3.2.0-1 -> 3.3.0-1\n", "")
        pkgs = PacmanManager().get_upgradable_packages()
        assert len(pkgs) == 1
        assert pkgs[0]["current_version"] == "3.2.0-1"
        assert pkgs[0]["version"] == "3.3.0-1"

    @patch("dashboard.services.packages.shutil.which")
    @patch("dashboard.services.packages.run_command")
    def test_get_upgradable_uses_checkupdates(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/checkupdates"
        mock_run.return_value = (0, "", "")
        PacmanManager().get_upgradable_packages()
        mock_run.assert_called_once_with(["/usr/bin/checkupdates"], timeout=25)

    @patch("dashboard.services.packages.run_command")
    def test_search_packages(self, mock_run):
        out = "core/htop 3.3.0-1\n    Interactive process viewer\n"
        mock_run.return_value = (0, out, "")
        results = PacmanManager().search_packages("htop")
        assert len(results) == 1
        assert results[0]["name"] == "htop"
        assert "Interactive" in results[0]["description"]


class TestDnfManager:
    def test_commands(self):
        mgr = DnfManager()
        assert mgr.get_install_command("htop") == ["dnf", "install", "-y", "htop"]
        assert mgr.get_remove_command("htop") == ["dnf", "remove", "-y", "htop"]
        assert mgr.get_upgrade_command() == ["dnf", "upgrade", "-y"]

    @patch("dashboard.services.packages.run_command")
    def test_get_installed_packages(self, mock_run):
        mock_run.return_value = (0, "htop\t3.3.0-1\tx86_64\n", "")
        pkgs = DnfManager().get_installed_packages()
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "htop"
        assert pkgs[0]["arch"] == "x86_64"

    @patch("dashboard.services.packages.run_command")
    def test_get_upgradable_packages_exit_100(self, mock_run):
        mock_run.return_value = (100, "htop 3.3.0-1\n", "")
        pkgs = DnfManager().get_upgradable_packages()
        assert len(pkgs) == 1

    @patch("dashboard.services.packages.run_command")
    def test_get_upgradable_packages_exit_0(self, mock_run):
        mock_run.return_value = (0, "", "")
        assert DnfManager().get_upgradable_packages() == []

    @patch("dashboard.services.packages.run_command")
    def test_get_upgradable_packages_error(self, mock_run):
        mock_run.return_value = (1, "", "err")
        assert DnfManager().get_upgradable_packages() == []


class TestGetPackageManager:
    def setup_method(self):
        import dashboard.services.packages as pkgs

        pkgs._CURRENT_MANAGER = None

    @patch("dashboard.services.packages.shutil.which")
    def test_detects_apk(self, mock_which):
        mock_which.side_effect = lambda x: "/sbin/apk" if x == "apk" else None
        mgr = get_package_manager()
        assert isinstance(mgr, ApkManager)

    @patch("dashboard.services.packages.shutil.which")
    def test_detects_apt(self, mock_which):
        mock_which.side_effect = lambda x: (
            "/usr/bin/dpkg-query" if x == "dpkg-query" else None
        )
        mgr = get_package_manager()
        assert isinstance(mgr, AptManager)

    @patch("dashboard.services.packages.shutil.which")
    def test_caches_manager(self, mock_which):
        mock_which.side_effect = lambda x: "/sbin/apk" if x == "apk" else None
        m1 = get_package_manager()
        m2 = get_package_manager()
        assert m1 is m2


class TestCacheAndWrappers:
    def setup_method(self):
        invalidate_packages_cache()
        import dashboard.services.packages as pkgs

        pkgs._CURRENT_MANAGER = None

    def test_invalidate_cache(self):
        _PACKAGES_CACHE["installed"] = [{"name": "x"}]
        _PACKAGES_CACHE["timestamp"] = time.time()
        invalidate_packages_cache()
        assert _PACKAGES_CACHE["installed"] is None
        assert _PACKAGES_CACHE["timestamp"] == 0.0

    @patch("dashboard.services.packages.get_package_manager")
    def test_get_installed_packages_caching(self, mock_get_mgr):
        mock_mgr = MagicMock()
        mock_mgr.get_installed_packages.return_value = [{"name": "htop"}]
        mock_get_mgr.return_value = mock_mgr

        result1 = get_installed_packages()
        result2 = get_installed_packages()
        assert result1 == result2
        mock_mgr.get_installed_packages.assert_called_once()

    @patch("dashboard.services.packages.get_package_manager")
    def test_get_installed_packages_force_refresh(self, mock_get_mgr):
        mock_mgr = MagicMock()
        mock_mgr.get_installed_packages.return_value = [{"name": "htop"}]
        mock_get_mgr.return_value = mock_mgr

        _PACKAGES_CACHE["installed"] = [{"name": "old"}]
        _PACKAGES_CACHE["timestamp"] = time.time()

        get_installed_packages(force_refresh=True)
        mock_mgr.get_installed_packages.assert_called_once()

    @patch("dashboard.services.packages.get_package_manager")
    def test_get_installed_count_from_cache(self, mock_get_mgr):
        _PACKAGES_CACHE["installed"] = [{"name": "a"}, {"name": "b"}]
        assert get_installed_count() == 2
        mock_get_mgr.assert_not_called()

    @patch("dashboard.services.packages.get_package_manager")
    def test_search_packages_empty_query(self, mock_get_mgr):
        assert search_packages("") == []
        assert search_packages("   ") == []
        mock_get_mgr.assert_not_called()

    @patch("dashboard.services.packages.run_sudo_command")
    @patch("dashboard.services.packages.get_package_manager")
    def test_upgrade_packages_no_cmd(self, mock_get_mgr, mock_sudo):
        mock_get_mgr.return_value = NullPackageManager()
        res = upgrade_packages()
        assert res["success"] is False
        assert "No upgrade command" in res["error"]

    @patch("dashboard.services.packages.run_sudo_command")
    @patch("dashboard.services.packages.get_package_manager")
    def test_install_package_success(self, mock_get_mgr, mock_sudo):
        mock_mgr = MagicMock()
        mock_mgr.get_install_command.return_value = ["apk", "add", "htop"]
        mock_get_mgr.return_value = mock_mgr
        mock_sudo.return_value = (0, "OK", "")
        res = install_package("htop")
        assert res["success"] is True

    @patch("dashboard.services.packages.run_sudo_command")
    @patch("dashboard.services.packages.get_package_manager")
    def test_remove_package_failure(self, mock_get_mgr, mock_sudo):
        mock_mgr = MagicMock()
        mock_mgr.get_remove_command.return_value = ["apk", "del", "htop"]
        mock_get_mgr.return_value = mock_mgr
        mock_sudo.return_value = (1, "", "permission denied")
        res = remove_package("htop")
        assert res["success"] is False
        assert res["error"] == "permission denied"
