"""Tests for AptManager."""

from dashboard.services.packages import AptManager


class TestAptManager:
    def test_id_attribute(self):
        mgr = AptManager()
        assert mgr.id == "apt"

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

    def test_is_available_when_dpkg_exists(self, mock_path_exists):
        mock_path_exists.return_value = True
        mgr = AptManager()
        assert mgr.is_available() is True

    def test_is_available_when_dpkg_missing(self, mock_path_exists):
        mock_path_exists.return_value = False
        mgr = AptManager()
        assert mgr.is_available() is False

    def test_get_installed_packages(
        self, mock_run_command, apt_installed_packages_output
    ):
        mock_run_command.return_value = apt_installed_packages_output
        mgr = AptManager()
        pkgs = mgr.get_installed_packages()

        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "htop"
        assert pkgs[0]["version"] == "3.3.0"
        assert pkgs[0]["arch"] == "amd64"
        assert pkgs[1]["name"] == "vim"
        assert pkgs[1]["version"] == "9.0"
        assert pkgs[1]["arch"] == "amd64"

    def test_get_installed_packages_fail(self, mock_run_command):
        mock_run_command.return_value = (1, "", "err")
        mgr = AptManager()
        pkgs = mgr.get_installed_packages()
        assert pkgs == []

    def test_get_upgradable_packages(self, mock_run_command):
        line = "htop/jammy-updates 3.3.0-1 amd64 [upgradable from: 3.2.0-1]"
        mock_run_command.return_value = (0, f"Listing...\n{line}\n", "")
        mgr = AptManager()
        pkgs = mgr.get_upgradable_packages()
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "htop"
        assert pkgs[0]["current_version"] == "3.2.0-1"

    def test_get_upgradable_packages_fail(self, mock_run_command):
        mock_run_command.return_value = (1, "", "err")
        pkgs = AptManager().get_upgradable_packages()
        assert len(pkgs) == 1
        assert "error" in pkgs[0]

    def test_search_packages_names_only(self, mock_run_command):
        mock_run_command.return_value = (0, "htop - interactive process viewer\n", "")
        results = AptManager().search_packages("htop")
        assert len(results) == 1
        assert results[0]["name"] == "htop"
        assert "interactive" in results[0]["description"]

    def test_search_packages_fallback(self, mock_run_command):
        mock_run_command.side_effect = [
            (0, "", ""),
            (0, "htop - interactive process viewer\n", ""),
        ]
        results = AptManager().search_packages("htop")
        assert len(results) == 1

    def test_search_packages_empty_results(self, mock_run_command):
        mock_run_command.return_value = (0, "", "")
        results = AptManager().search_packages("htop")
        assert results == []

    def test_get_package_info_dpkg(self, mock_run_command):
        mock_run_command.return_value = (0, "Package: htop\nVersion: 3.3.0\n", "")
        info = AptManager().get_package_info("htop")
        assert "htop" in info["info"]
        assert "3.3.0" in info["info"]

    def test_get_package_info_fallback_apt_cache(self, mock_run_command):
        mock_run_command.side_effect = [
            (1, "", "not installed"),
            (0, "Package: htop\n", ""),
        ]
        info = AptManager().get_package_info("htop")
        assert "htop" in info["info"]

    def test_get_package_info_fail(self, mock_run_command):
        mock_run_command.return_value = (1, "", "not found")
        info = AptManager().get_package_info("htop")
        assert "error" in info
        assert "not found" in info["error"]

    def test_get_installed_packages_handles_malformed_output(self, mock_run_command):
        """Test parsing when output doesn't match expected format."""
        mock_run_command.return_value = (
            0,
            "invalid-line-no-tab\nanother-bad-line\n",
            "",
        )
        mgr = AptManager()
        pkgs = mgr.get_installed_packages()
        # Should handle gracefully, not crash
        assert isinstance(pkgs, list)

    def test_get_installed_packages_handles_empty_output(self, mock_run_command):
        """Test parsing when output is empty."""
        mock_run_command.return_value = (0, "", "")
        mgr = AptManager()
        pkgs = mgr.get_installed_packages()
        assert pkgs == []
