"""Tests for DnfManager."""

from dashboard.services.packages import DnfManager


class TestDnfManager:
    def test_id_attribute(self):
        mgr = DnfManager()
        assert mgr.id == "dnf"

    def test_is_available_when_dnf_exists(self, mock_path_exists):
        mock_path_exists.return_value = True
        mgr = DnfManager()
        assert mgr.is_available() is True

    def test_is_available_when_dnf_missing(self, mock_path_exists):
        mock_path_exists.return_value = False
        mgr = DnfManager()
        assert mgr.is_available() is False

    def test_get_install_command(self):
        mgr = DnfManager()
        assert mgr.get_install_command("htop") == ["dnf", "install", "-y", "htop"]

    def test_get_upgrade_command(self):
        mgr = DnfManager()
        assert mgr.get_upgrade_command() == ["dnf", "upgrade", "-y"]

    def test_get_upgradable_packages(self, mock_run_command):
        mock_run_command.return_value = (
            0,
            "htop.x86_64 3.3.0-1 updates",
            "",
        )
        mgr = DnfManager()
        pkgs = mgr.get_upgradable_packages()
        assert len(pkgs) == 1
        # dnf check-update output: "name.arch version repo"
        assert pkgs[0]["name"] == "htop.x86_64"
        assert pkgs[0]["version"] == "3.3.0-1"
        assert pkgs[0]["repo"] == "updates"

    def test_get_upgradable_packages_error(self, mock_run_command):
        mock_run_command.return_value = (1, "", "err")
        mgr = DnfManager()
        pkgs = mgr.get_upgradable_packages()
        assert pkgs == []

    def test_search_packages(self, mock_run_command):
        mock_run_command.return_value = (
            0,
            "htop.x86_64\t3.3.0-1 updates Interactive process viewer\n",
            "",
        )
        results = DnfManager().search_packages("htop")
        assert len(results) == 1
        # Mock output format: "name.arch\tversion repo description"
        assert results[0]["name"] == "htop"
        assert results[0]["version"] == "3.3.0-1 updates Interactive process viewer"
        assert results[0]["arch"] == "x86_64"

    def test_search_packages_empty_results(self, mock_run_command):
        mock_run_command.return_value = (0, "", "")
        results = DnfManager().search_packages("htop")
        assert results == []

    def test_search_packages_fail(self, mock_run_command):
        mock_run_command.return_value = (1, "", "err")
        results = DnfManager().search_packages("htop")
        assert len(results) == 1
        assert results[0]["error"] == "err"

    def test_get_installed_packages_handles_malformed_output(self, mock_run_command):
        """Test parsing when output doesn't match expected format."""
        mock_run_command.return_value = (
            0,
            "invalid-line-no-tab\nanother-bad-line\n",
            "",
        )
        mgr = DnfManager()
        pkgs = mgr.get_installed_packages()
        # Should handle gracefully, not crash
        assert isinstance(pkgs, list)

    def test_get_installed_packages_handles_empty_output(self, mock_run_command):
        """Test parsing when output is empty."""
        mock_run_command.return_value = (0, "", "")
        mgr = DnfManager()
        pkgs = mgr.get_installed_packages()
        assert pkgs == []
