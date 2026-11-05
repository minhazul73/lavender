from unittest.mock import patch

from server.services.packages import ApkManager


class TestApkManager:
    def test_commands(self):
        mgr = ApkManager()
        assert mgr.get_install_command("htop") == ["apk", "add", "htop"]
        assert mgr.get_remove_command("htop") == ["apk", "del", "htop"]
        assert mgr.get_upgrade_command() == ["apk", "upgrade"]
        assert mgr.get_upgrade_command("htop") == ["apk", "add", "-u", "htop"]

    @patch("server.services.packages.run_command")
    def test_get_installed_packages_parses_v_output(self, mock_run):
        mock_run.return_value = (0, "musl-1.2.4-r0\nbusybox-1.36.1-r2\n", "")
        manager = ApkManager()
        pkgs = manager.get_installed_packages()
        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "busybox"
        assert pkgs[0]["version"] == "1.36.1-r2"
        assert pkgs[1]["name"] == "musl"

    @patch("server.services.packages.run_command")
    def test_get_installed_packages_fallback_to_info(self, mock_run):
        mock_run.side_effect = [(1, "", "err"), (0, "musl\nbusybox\n", "")]
        manager = ApkManager()
        pkgs = manager.get_installed_packages()
        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "busybox"
        assert pkgs[0]["version"] == ""

    @patch("server.services.packages.run_command")
    def test_get_installed_packages_all_fail(self, mock_run):
        mock_run.return_value = (1, "", "err")
        assert ApkManager().get_installed_packages() == []

    @patch("server.services.packages.run_command")
    def test_get_installed_count(self, mock_run):
        mock_run.return_value = (0, "a\nb\nc\n", "")
        assert ApkManager().get_installed_count() == 3

    @patch("server.services.packages.run_command")
    def test_get_installed_count_fail(self, mock_run):
        mock_run.return_value = (1, "", "err")
        assert ApkManager().get_installed_count() == 0

    @patch("server.services.packages.run_command")
    def test_get_upgradable_packages(self, mock_run):
        mock_run.return_value = (
            0,
            "busybox-1.36.1-r3 aarch64 {busybox} [upgradable from: busybox-1.36.1-r2]\n",
            "",
        )
        pkgs = ApkManager().get_upgradable_packages()
        assert len(pkgs) == 1
        assert pkgs[0]["current_version"] == "busybox-1.36.1-r2"

    @patch("server.services.packages.run_command")
    def test_get_upgradable_packages_fail(self, mock_run):
        mock_run.return_value = (1, "", "network error")
        pkgs = ApkManager().get_upgradable_packages()
        assert pkgs[0]["error"] == "network error"

    @patch("server.services.packages.run_command")
    def test_search_packages(self, mock_run):
        mock_run.return_value = (0, "htop-3.3.0-r0\n", "")
        results = ApkManager().search_packages("htop")
        assert len(results) == 1
        assert results[0]["name"] == "htop"

    @patch("server.services.packages.run_command")
    def test_search_packages_fail(self, mock_run):
        mock_run.return_value = (1, "", "err")
        results = ApkManager().search_packages("htop")
        assert results[0]["error"] == "err"

    @patch("server.services.packages.run_command")
    def test_get_package_info(self, mock_run):
        mock_run.return_value = (0, "htop description", "")
        info = ApkManager().get_package_info("htop")
        assert info["info"] == "htop description"
        assert info["error"] is None
