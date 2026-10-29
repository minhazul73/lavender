"""Tests for ApkManager."""

from dashboard.services.packages import ApkManager


class TestApkManager:
    def test_id_attribute(self):
        mgr = ApkManager()
        assert mgr.id == "apk"

    def test_commands(self):
        mgr = ApkManager()
        assert mgr.get_install_command("htop") == ["apk", "add", "htop"]
        assert mgr.get_remove_command("htop") == ["apk", "del", "htop"]
        assert mgr.get_upgrade_command() == ["apk", "upgrade"]
        assert mgr.get_upgrade_command("htop") == ["apk", "add", "-u", "htop"]

    def test_is_available_when_apk_exists(self, mock_path_exists):
        mock_path_exists.return_value = True
        mgr = ApkManager()
        assert mgr.is_available() is True

    def test_is_available_when_apk_missing(self, mock_path_exists):
        mock_path_exists.return_value = False
        mgr = ApkManager()
        assert mgr.is_available() is False

    def test_get_installed_packages_parses_v_output(
        self, mock_run_command, apk_installed_packages_output
    ):
        mock_run_command.return_value = apk_installed_packages_output
        mgr = ApkManager()
        pkgs = mgr.get_installed_packages()

        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "busybox"
        assert pkgs[0]["version"] == "1.36.1-r2"
        assert pkgs[1]["name"] == "musl"
        assert pkgs[1]["version"] == "1.2.4-r0"

    def test_get_installed_packages_fallback_to_info(self, mock_run_command):
        mock_run_command.side_effect = [
            (1, "", "err"),
            (0, "musl\nbusybox\n", ""),
        ]
        mgr = ApkManager()
        pkgs = mgr.get_installed_packages()

        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "busybox"
        assert pkgs[0]["version"] == ""
        assert pkgs[1]["name"] == "musl"
        assert pkgs[1]["version"] == ""

    def test_get_installed_packages_all_fail(self, mock_run_command):
        mock_run_command.return_value = (1, "", "err")
        mgr = ApkManager()
        pkgs = mgr.get_installed_packages()
        assert pkgs == []

    def test_get_installed_count(self, mock_run_command):
        mock_run_command.return_value = (0, "a\nb\nc\n", "")
        mgr = ApkManager()
        assert mgr.get_installed_count() == 3

    def test_get_installed_count_fail(self, mock_run_command):
        mock_run_command.return_value = (1, "", "err")
        mgr = ApkManager()
        assert mgr.get_installed_count() == 0

    def test_get_upgradable_packages(self, mock_run_command):
        mock_run_command.return_value = (
            0,
            "busybox-1.36.1-r3 aarch64 {busybox} "
            "[upgradable from: busybox-1.36.1-r2]\n",
            "",
        )
        mgr = ApkManager()
        pkgs = mgr.get_upgradable_packages()
        assert len(pkgs) == 1
        assert pkgs[0]["current_version"] == "busybox-1.36.1-r2"

    def test_get_upgradable_packages_fail(self, mock_run_command):
        mock_run_command.return_value = (1, "", "network error")
        pkgs = ApkManager().get_upgradable_packages()
        assert len(pkgs) == 1
        assert pkgs[0]["error"] == "network error"

    def test_search_packages(self, mock_run_command):
        mock_run_command.return_value = (0, "htop-3.3.0-r0\n", "")
        results = ApkManager().search_packages("htop")
        assert len(results) == 1
        assert results[0]["name"] == "htop"

    def test_search_packages_fail(self, mock_run_command):
        mock_run_command.return_value = (1, "", "err")
        results = ApkManager().search_packages("htop")
        assert len(results) == 1
        assert results[0]["error"] == "err"

    def test_get_package_info(self, mock_run_command):
        mock_run_command.return_value = (0, "htop description", "")
        info = ApkManager().get_package_info("htop")
        assert info["package"] == "htop"
        assert info["info"] == "htop description"
        assert info["error"] is None

    def test_get_package_info_fail(self, mock_run_command):
        mock_run_command.return_value = (1, "", "not found")
        info = ApkManager().get_package_info("htop")
        assert "error" in info
        assert "not found" in info["error"]

    def test_get_installed_packages_handles_malformed_output(self, mock_run_command):
        """Test parsing when output doesn't match expected format."""
        mock_run_command.return_value = (
            0,
            "invalid-line-no-dash\nanother-bad-line\n",
            "",
        )
        mgr = ApkManager()
        pkgs = mgr.get_installed_packages()
        # Should handle gracefully, not crash
        assert isinstance(pkgs, list)

    def test_get_installed_packages_handles_empty_output(self, mock_run_command):
        """Test parsing when output is empty."""
        mock_run_command.return_value = (0, "", "")
        mgr = ApkManager()
        pkgs = mgr.get_installed_packages()
        assert pkgs == []
